"""Scheduler for polling smart contract and managing Docker containers."""
import logging
import json
from typing import Optional
from web3 import Web3
import docker
import trio

logger = logging.getLogger(__name__)


class CanteenScheduler:
    """Manages container scheduling based on smart contract state."""
    
    def __init__(self, cluster, contract_address: str, provider_url: str, private_key: str):
        """Initialize scheduler.
        
        Args:
            cluster: CanteenCluster instance
            contract_address: Ethereum contract address
            provider_url: Blockchain provider URL
            private_key: Private key for transactions (empty to use Ganache account)
        """
        self.cluster = cluster
        self.contract_address = contract_address
        self.provider_url = provider_url
        self.private_key = private_key
        
        # Will be initialized in start()
        self.w3 = None
        self.contract = None
        self.account = None
        self.docker_client = None
        
        # Container state
        self.current_container = None
        self.current_image = None
    
    async def initialize(self):
        """Initialize the scheduler components."""
        logger.info("Initializing scheduler...")
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.provider_url))
        
        if not self.w3.is_connected():
            raise Exception(f"Failed to connect to blockchain at {self.provider_url}")
        
        logger.info(f"✓ Connected to blockchain")
        
        # Get account
        if self.private_key:
            account = self.w3.eth.account.from_key(self.private_key)
            self.account = account.address
            logger.info(f"Using private key account: {self.account}")
        else:
            # Use first Ganache account
            accounts = self.w3.eth.accounts
            if not accounts:
                raise Exception("No accounts available in Ganache")
            self.account = accounts[0]
            logger.info(f"Using Ganache account: {self.account}")
        
        # Load contract
        contract_path = 'build/contracts/Canteen.json'
        try:
            with open(contract_path) as f:
                contract_json = json.load(f)
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=contract_json['abi']
                )
            logger.info(f"✓ Loaded contract from {contract_path}")
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
            raise
        
        # Initialize Docker client
        try:
            self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            self.docker_client.ping()
            logger.info("✓ Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
        
        # Register node with contract
        await self.register_node()
        
        logger.info("✓ Scheduler initialized")
    
    async def register_node(self):
        """Register this node with the smart contract."""
        host_id = self.cluster.get_host()
        logger.info(f"Registering node with contract: {host_id}")
        
        try:
            # Call addMember function
            tx_hash = self.contract.functions.addMember(host_id).transact({
                'from': self.account,
                'gas': 300000
            })
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"✓ Node registered successfully (tx: {tx_hash.hex()[:10]}...)")
            else:
                logger.error(f"Transaction failed: {receipt}")
        except Exception as e:
            error_msg = str(e)
            if "revert" in error_msg.lower():
                logger.info("Node seems to have existed previously. Continuing...")
            else:
                logger.error(f"Failed to register node: {e}")
                raise
    
    async def poll_loop(self, interval: float):
        """Poll contract for image assignment and manage containers.
        
        Args:
            interval: Polling interval in seconds
        """
        host_id = self.cluster.get_host()
        
        while True:
            try:
                # Query contract for assigned image
                details = self.contract.functions.getMemberDetails(host_id).call()
                scheduled_image = details[0]  # imageName from Member struct
                
                # Check if image assignment changed
                if scheduled_image != self.current_image:
                    logger.info(f"Image assignment changed: '{self.current_image}' -> '{scheduled_image}'")
                    
                    if scheduled_image:
                        await self.update_container(scheduled_image)
                    else:
                        await self.cleanup_container()
                
            except Exception as e:
                logger.error(f"Error in poll loop: {e}")
            
            await trio.sleep(interval)
    
    async def update_container(self, image_name: str):
        """Pull and run a Docker container.
        
        Args:
            image_name: Docker image name (e.g., 'nginx:latest')
        """
        logger.info(f"Updating container to image: {image_name}")
        
        try:
            # Run Docker operations in thread pool (they're blocking)
            # Pull image
            logger.info(f"Pulling image: {image_name}...")
            await trio.to_thread.run_sync(
                lambda: self.docker_client.images.pull(image_name)
            )
            logger.info(f"✓ Image pulled: {image_name}")
            
            # Stop and remove old container
            if self.current_container:
                logger.info("Stopping old container...")
                await trio.to_thread.run_sync(self._stop_container)
            
            # Determine port
            port = 8000 if "hello-world" in image_name else 8080
            
            # Create and start new container
            logger.info(f"Starting new container (port {port})...")
            container = await trio.to_thread.run_sync(
                lambda: self.docker_client.containers.run(
                    image_name,
                    detach=True,
                    ports={f'{port}/tcp': port},
                    remove=False
                )
            )
            
            self.current_container = container
            self.current_image = image_name
            
            logger.info(f"✓ Container started: {container.id[:12]}")
            logger.info(f"  Image: {image_name}")
            logger.info(f"  Port: {port}")
            
        except Exception as e:
            logger.error(f"Failed to update container: {e}")
            raise
    
    def _stop_container(self):
        """Stop current container (blocking operation)."""
        if self.current_container:
            try:
                self.current_container.stop(timeout=10)
                self.current_container.remove()
                logger.info(f"✓ Old container stopped and removed")
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")
    
    async def cleanup_container(self):
        """Clean up current container."""
        logger.info("Cleaning up container...")
        
        if self.current_container:
            await trio.to_thread.run_sync(self._stop_container)
            
            self.current_container = None
            self.current_image = None
            logger.info("✓ Container cleaned up")
        else:
            logger.info("No container to clean up")
    
    async def cleanup(self):
        """Cleanup scheduler resources."""
        logger.info("Cleaning up scheduler...")
        await self.cleanup_container()
