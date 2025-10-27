"""
Client node for sending scheduling commands to operator nodes via P2P.

This client connects to operator nodes using libp2p and sends Docker image 
deployment requests with replica counts over P2P streams. The operator nodes 
then schedule the containers across the cluster using the smart contract.
"""
import argparse
import json
import logging
import sys
import trio
from typing import Optional
from multiaddr import Multiaddr

from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr
from protocol import (
    DEPLOYMENT_PROTOCOL_ID,
    DeploymentRequest,
    DeploymentResponse,
    StatusRequest,
    StatusResponse
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


class CanteenClient:
    """P2P client for interacting with Canteen operator nodes."""
    
    def __init__(self, operator_multiaddr: str):
        """Initialize client with operator node multiaddr.
        
        Args:
            operator_multiaddr: Multiaddr of operator node (e.g., '/ip4/127.0.0.1/tcp/5000/p2p/Qm...')
        """
        self.operator_multiaddr = Multiaddr(operator_multiaddr)
        self.host = None
        logger.info(f"Initialized P2P client")
        logger.info(f"  Target operator: {operator_multiaddr}")
    
    async def _send_request(self, request: DeploymentRequest) -> DeploymentResponse:
        """Send a deployment request to the operator over P2P stream.
        
        Args:
            request: The deployment request to send
            
        Returns:
            DeploymentResponse from the operator
        """
        try:
            # Parse operator multiaddr to get peer info
            logger.info(f"Parsing operator address...")
            info = info_from_p2p_addr(self.operator_multiaddr)
            
            # Connect to operator
            logger.info(f"Connecting to operator {info.peer_id.pretty()}...")
            await self.host.connect(info)
            logger.info(f"✓ Connected to operator")
            
            # Open stream with deployment protocol
            logger.info(f"Opening deployment stream...")
            stream = await self.host.new_stream(
                info.peer_id,
                [DEPLOYMENT_PROTOCOL_ID]
            )
            logger.info(f"✓ Stream opened")
            
            # Send request
            logger.info(f"Sending {request.action} request...")
            await stream.write(request.to_bytes())
            
            # Read response (with timeout)
            logger.info(f"Waiting for response...")
            response_data = await stream.read(8192)  # Max 8KB response
            
            if not response_data:
                raise Exception("No response from operator")
            
            response = DeploymentResponse.from_bytes(response_data)
            logger.info(f"✓ Received response")
            
            # Close stream
            await stream.close()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to communicate with operator: {e}")
            raise
    
    async def _send_status_request(self) -> StatusResponse:
        """Send a status request to get cluster info.
        
        Returns:
            StatusResponse with cluster information
        """
        try:
            # Parse operator multiaddr to get peer info
            logger.info(f"Connecting to operator for status...")
            info = info_from_p2p_addr(self.operator_multiaddr)
            
            # Connect to operator
            await self.host.connect(info)
            
            # Open stream
            stream = await self.host.new_stream(
                info.peer_id,
                [DEPLOYMENT_PROTOCOL_ID]
            )
            
            # Send status request
            status_req = StatusRequest()
            await stream.write(status_req.to_bytes())
            
            # Read response
            response_data = await stream.read(16384)  # Max 16KB for status
            
            if not response_data:
                raise Exception("No status response from operator")
            
            response = StatusResponse.from_bytes(response_data)
            
            # Close stream
            await stream.close()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get status from operator: {e}")
            raise
    
    async def deploy_image(self, image_name: str, replicas: int = 1) -> dict:
        """Deploy a Docker image with specified replicas.
        
        Args:
            image_name: Docker image to deploy (e.g., 'nginx:latest')
            replicas: Number of replicas to run across the cluster
            
        Returns:
            Dictionary with deployment result
        """
        logger.info(f"Deploying {image_name} with {replicas} replica(s)...")
        
        request = DeploymentRequest(
            action="deploy",
            image=image_name,
            replicas=replicas
        )
        
        response = await self._send_request(request)
        
        if response.success:
            logger.info(f"✓ Deployment successful!")
            logger.info(f"  Image: {response.image}")
            logger.info(f"  Replicas: {response.replicas}")
        else:
            logger.error(f"✗ Deployment failed: {response.error}")
        
        return {
            'success': response.success,
            'image': response.image,
            'replicas': response.replicas,
            'message': response.message,
            'error': response.error
        }
    
    async def get_cluster_status(self) -> dict:
        """Get cluster status from operator.
        
        Returns:
            Dictionary with cluster status information
        """
        logger.info("Getting cluster status...")
        
        response = await self._send_status_request()
        
        if response.success:
            logger.info(f"✓ Cluster status retrieved")
            logger.info(f"  Total members: {response.total_members}")
            logger.info(f"  Connected: {response.connected_count}")
        else:
            logger.error(f"✗ Failed to get status: {response.error}")
        
        return {
            'success': response.success,
            'total_members': response.total_members,
            'connected_count': response.connected_count,
            'members': response.members,
            'error': response.error
        }
    
    async def remove_deployment(self, image_name: str) -> dict:
        """Remove all instances of a deployed image.
        
        Args:
            image_name: Docker image to remove
            
        Returns:
            Dictionary with removal result
        """
        logger.info(f"Removing deployment: {image_name}")
        
        request = DeploymentRequest(
            action="undeploy",
            image=image_name,
            replicas=0  # Not used for undeploy
        )
        
        response = await self._send_request(request)
        
        if response.success:
            logger.info(f"✓ Removal successful!")
        else:
            logger.error(f"✗ Removal failed: {response.error}")
        
        return {
            'success': response.success,
            'image': image_name,
            'message': response.message,
            'error': response.error
        }



async def run_client(args):
    """Run the client with given arguments."""
    # Create client
    client = CanteenClient(args.operator)
    
    # Create host
    host = new_host()
    listen_addrs = [Multiaddr("/ip4/0.0.0.0/tcp/0")]
    
    logger.info("Starting libp2p client host...")
    
    # Use async context manager like chat.py example
    async with host.run(listen_addrs=listen_addrs):
        client.host = host
        logger.info(f"✓ Client host started")
        logger.info(f"  Peer ID: {host.get_id().pretty()}")
        
        try:
            # Execute command
            if args.command == 'deploy':
                result = await client.deploy_image(args.image, args.replicas)
                print(json.dumps(result, indent=2))
                
            elif args.command == 'status':
                status = await client.get_cluster_status()
                print(json.dumps(status, indent=2))
                
            elif args.command == 'remove':
                result = await client.remove_deployment(args.image)
                print(json.dumps(result, indent=2))
            
        except Exception as e:
            logger.error(f"Client error: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Canteen P2P Client - Deploy containers to operator nodes via libp2p',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Deploy nginx with 3 replicas
  python python/client.py --operator /ip4/127.0.0.1/tcp/5000/p2p/QmXXX... deploy nginx:latest --replicas 3
  
  # Get cluster status
  python python/client.py --operator /ip4/127.0.0.1/tcp/5000/p2p/QmXXX... status
  
  # Remove deployment
  python python/client.py --operator /ip4/127.0.0.1/tcp/5000/p2p/QmXXX... remove nginx:latest

Note: Get the operator's full multiaddr from the operator node logs at startup.
      It will look like: /ip4/127.0.0.1/tcp/5000/p2p/QmNk1pX27NLvMZUQKQcbHrcJ594sQ2t21hNKUH7K9oVfPP
        '''
    )
    
    parser.add_argument(
        '--operator',
        required=True,
        help='Multiaddr of operator node (e.g., /ip4/127.0.0.1/tcp/5000/p2p/QmXXX...)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy a Docker image')
    deploy_parser.add_argument('image', help='Docker image name (e.g., nginx:latest)')
    deploy_parser.add_argument('--replicas', type=int, default=1, help='Number of replicas (default: 1)')
    
    # Status command
    subparsers.add_parser('status', help='Get cluster status')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a deployment')
    remove_parser.add_argument('image', help='Docker image name to remove')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run with trio
    trio.run(run_client, args)


if __name__ == '__main__':
    main()
