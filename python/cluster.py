"""Cluster management using py-libp2p with mDNS discovery."""
import json
import logging
from typing import List
import multiaddr
import trio
from libp2p import new_host
from libp2p.abc import PeerInfo
from libp2p.discovery.events.peerDiscovery import peerDiscovery

from protocol import (
    DEPLOYMENT_PROTOCOL_ID,
    DeploymentRequest,
    DeploymentResponse,
    StatusRequest,
    StatusResponse
)

logger = logging.getLogger(__name__)        


class CanteenCluster:
    """Manages P2P cluster using libp2p with mDNS discovery."""
    
    def __init__(self, port: int, namespace: str, scheduler=None):
        """Initialize cluster manager.
        
        Args:
            port: Port to listen on
            namespace: Service name for mDNS discovery (not used with auto mDNS)
            scheduler: Reference to scheduler for handling deployment requests
        """
        self.port = port
        self.namespace = namespace
        self.host = None
        self.connected_peers = set()
        self.peer_id = None
        self.ready_event = trio.Event()  # Signal when cluster is ready
        self.nursery = None  # Will hold the nursery for spawning tasks
        self.scheduler = scheduler  # Reference to scheduler for contract operations
        
    def set_scheduler(self, scheduler):
        """Set scheduler reference after initialization."""
        self.scheduler = scheduler
        
    async def _handle_deployment_stream(self, stream):
        """Handle incoming deployment requests from P2P clients.
        
        Args:
            stream: The libp2p stream from the client
        """
        try:
            logger.info(f"Received deployment stream from client")
            
            # Read request
            request_data = await stream.read(8192)  # Max 8KB request
            
            if not request_data:
                logger.warning("Empty deployment request")
                return
            
            # Parse request
            try:
                # Try to parse as DeploymentRequest
                request = DeploymentRequest.from_bytes(request_data)
                
                if request.action == "deploy":
                    response = await self._handle_deploy(request)
                elif request.action == "undeploy":
                    response = await self._handle_undeploy(request)
                else:
                    response = DeploymentResponse(
                        success=False,
                        message="Unknown action",
                        error=f"Unknown action: {request.action}"
                    )
            except:
                # Maybe it's a status request
                status_req = json.loads(request_data[4:].decode('utf-8'))
                if status_req.get('action') == 'status':
                    response = await self._handle_status()
                else:
                    raise
            
            # Send response
            await stream.write(response.to_bytes())
            logger.info(f"✓ Sent deployment response")
            
            # Close stream
            await stream.close()
            
        except Exception as e:
            logger.error(f"Error handling deployment stream: {e}")
            try:
                # Try to send error response
                error_response = DeploymentResponse(
                    success=False,
                    message="Internal error",
                    error=str(e)
                )
                await stream.write(error_response.to_bytes())
                await stream.close()
            except:
                pass
    
    async def _handle_deploy(self, request: DeploymentRequest) -> DeploymentResponse:
        """Handle a deploy request."""
        try:
            logger.info(f"Processing deploy request: {request.image} x{request.replicas}")
            
            if not self.scheduler:
                return DeploymentResponse(
                    success=False,
                    message="Scheduler not available",
                    error="No scheduler configured"
                )
            
            # Use addImage contract function
            await trio.to_thread.run_sync(
                lambda: self.scheduler.contract.functions.addImage(
                    request.image,
                    request.replicas
                ).transact({
                    'from': self.scheduler.account,
                    'gas': 6000000  # Optimized contract with mappings
                })
            )
            
            logger.info(f"✓ Added image to contract: {request.image} x{request.replicas}")
            
            return DeploymentResponse(
                success=True,
                message=f"Deployed {request.image} with {request.replicas} replicas",
                image=request.image,
                replicas=request.replicas
            )
            
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return DeploymentResponse(
                success=False,
                message="Deployment failed",
                error=str(e)
            )
    
    async def _handle_undeploy(self, request: DeploymentRequest) -> DeploymentResponse:
        """Handle an undeploy request."""
        try:
            logger.info(f"Processing undeploy request: {request.image}")
            
            if not self.scheduler:
                return DeploymentResponse(
                    success=False,
                    message="Scheduler not available",
                    error="No scheduler configured"
                )
            
            # Use removeImage contract function
            await trio.to_thread.run_sync(
                lambda: self.scheduler.contract.functions.removeImage(
                    request.image
                ).transact({
                    'from': self.scheduler.account,
                    'gas': 6000000  # Optimized contract
                })
            )
            
            logger.info(f"✓ Removed image from contract: {request.image}")
            
            return DeploymentResponse(
                success=True,
                message=f"Removed deployment: {request.image}",
                image=request.image
            )
            
        except Exception as e:
            logger.error(f"Undeploy failed: {e}")
            return DeploymentResponse(
                success=False,
                message="Removal failed",
                error=str(e)
            )
    
    async def _handle_status(self) -> StatusResponse:
        """Handle a status request."""
        try:
            if not self.scheduler:
                return StatusResponse(
                    success=False,
                    total_members=0,
                    connected_count=0,
                    members=[],
                    error="Scheduler not available"
                )
            
            # Get members from contract
            members = self.scheduler.get_contract_members()
            connected = self.get_connected_peers()
            
            return StatusResponse(
                success=True,
                total_members=len(members),
                connected_count=len(connected),
                members=members
            )
            
        except Exception as e:
            logger.error(f"Status request failed: {e}")
            return StatusResponse(
                success=False,
                total_members=0,
                connected_count=0,
                members=[],
                error=str(e)
            )
        
    def _on_peer_discovered(self, peer_info: PeerInfo):
        """Callback when a peer is discovered via mDNS.
        
        Note: This is a sync function because the mDNS library calls it without await.
        """
        peer_id = str(peer_info.peer_id)
        
        # Skip if it's ourselves
        if self.peer_id and peer_id == str(self.peer_id):
            return
        
        # Add to discovered set
        if peer_id not in self.connected_peers:
            self.connected_peers.add(peer_id)
            logger.info(f"✓ Discovered peer via mDNS: {peer_id}")
            
            # Note: We can't do async operations here since this is a sync callback
            # The peer will be available in the peerstore for future connections
            if self.nursery:
                self.nursery.start_soon(self._connect_to_peer, peer_info)
    
    async def _connect_to_peer(self, peer_info: PeerInfo):
        """Connect to a discovered peer."""
        peer_id = str(peer_info.peer_id)
        try:
            logger.info(f"Attempting to connect to {peer_id}...")
            await self.host.connect(peer_info)
            logger.info(f"✓ Successfully connected to peer: {peer_id}")
        except Exception as e:
            logger.debug(f"Could not connect to {peer_id}: {e}")
    
    def get_connected_peers(self) -> List[str]:
        """Get actually connected peers from the swarm."""
        if not self.host:
            return []
        
        # Get peers from the swarm's network (actual connections)
        connected = []
        try:
            peers = self.host.get_network().connections
            for peer_id in peers.keys():
                connected.append(str(peer_id))
        except Exception as e:
            logger.debug(f"Error getting connected peers: {e}")
        
        return connected
    
    async def start(self):
        """Start the cluster node (must be called inside a nursery)."""
        logger.info(f"Starting cluster node on port {self.port}...")
        
        # Register peer discovery callback
        peerDiscovery.register_peer_discovered_handler(self._on_peer_discovered)
        
        # Create libp2p host with mDNS enabled
        listen_addrs = [multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{self.port}")]
        self.host = new_host(enable_mDNS=True)
        
        # Register deployment protocol handler
        self.host.set_stream_handler(DEPLOYMENT_PROTOCOL_ID, self._handle_deployment_stream)
        logger.info(f"✓ Registered deployment protocol handler: {DEPLOYMENT_PROTOCOL_ID}")
        
        # Start the host with the context manager
        logger.info(f"Starting libp2p host with mDNS discovery...")
        async with self.host.run(listen_addrs=listen_addrs):
            logger.info(f"Libp2p host started, retrieving peer ID...")
            self.peer_id = self.host.get_id()
            
            # Get actual listening addresses
            actual_addrs = self.host.get_addrs()
            logger.info(f"Peer ID: {self.peer_id}")
            
            # Print full multiaddr for client use - build from port and peer_id
            full_multiaddr = f"/ip4/127.0.0.1/tcp/{self.port}/p2p/{self.peer_id}"
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("OPERATOR NODE READY - Connect clients with this multiaddr:")
            logger.info("")
            logger.info(f"  {full_multiaddr}")
            logger.info("")
            logger.info("=" * 80)
            logger.info("")
            
            logger.info(f"✓ Cluster node started successfully with mDNS discovery")
            logger.info("  Waiting for peers on local network...")
            
            # Signal that cluster is ready with valid peer_id
            self.ready_event.set()
            logger.info("✓ Cluster ready event set - scheduler can now initialize")
            
            # Create a nursery for peer connections and keep running
            async with trio.open_nursery() as nursery:
                self.nursery = nursery
                # Keep running until cancelled
                await trio.sleep_forever()
    
    def get_host(self) -> str:
        """Get host identifier (peer ID)."""
        return str(self.peer_id) if self.peer_id else "unknown"
    
    def get_members(self) -> List[str]:
        """Get list of connected peer IDs (live connections only)."""
        # Return actual connected peers from swarm, not just discovered ones
        return self.get_connected_peers()

    
    async def cleanup(self):
        """Cleanup cluster resources."""
        logger.info("Cleaning up cluster...")
        # Cleanup is handled by the context manager in start()
        logger.info("✓ Cluster cleaned up")

