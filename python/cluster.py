"""Cluster management using py-libp2p with mDNS discovery."""
import logging
from typing import List
import multiaddr
import trio
from libp2p import new_host
from libp2p.abc import PeerInfo
from libp2p.discovery.events.peerDiscovery import peerDiscovery

logger = logging.getLogger(__name__)        


class CanteenCluster:
    """Manages P2P cluster using libp2p with mDNS discovery."""
    
    def __init__(self, port: int, namespace: str):
        """Initialize cluster manager.
        
        Args:
            port: Port to listen on
            namespace: Service name for mDNS discovery (not used with auto mDNS)
        """
        self.port = port
        self.namespace = namespace
        self.host = None
        self.connected_peers = set()
        self.peer_id = None
        self.ready_event = trio.Event()  # Signal when cluster is ready
        
    def _on_peer_discovered(self, peer_info: PeerInfo):
        """Callback when a peer is discovered via mDNS."""
        peer_id = str(peer_info.peer_id)
        if peer_id != str(self.peer_id) and peer_id not in self.connected_peers:
            self.connected_peers.add(peer_id)
            logger.info(f"✓ Discovered peer via mDNS: {peer_id}")
        
    async def start(self):
        """Start the cluster node (must be called inside a nursery)."""
        logger.info(f"Starting cluster node on port {self.port}...")
        
        # Register peer discovery callback
        peerDiscovery.register_peer_discovered_handler(self._on_peer_discovered)
        
        # Create libp2p host with mDNS enabled
        listen_addrs = [multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{self.port}")]
        self.host = new_host(enable_mDNS=True)
        
        # Start the host with the context manager
        logger.info(f"Starting libp2p host with mDNS discovery...")
        async with self.host.run(listen_addrs=listen_addrs):
            logger.info(f"Libp2p host started, retrieving peer ID...")
            self.peer_id = self.host.get_id()
            
            # Get actual listening addresses
            actual_addrs = self.host.get_addrs()
            logger.info(f"Peer ID: {self.peer_id}")
            logger.info(f"Listening on: {actual_addrs}")
            logger.info(f"✓ Cluster node started successfully with mDNS discovery")
            logger.info("  Waiting for peers on local network...")
            
            # Signal that cluster is ready with valid peer_id
            self.ready_event.set()
            logger.info("✓ Cluster ready event set - scheduler can now initialize")
            
            # Keep running until cancelled
            await trio.sleep_forever()
    
    def get_host(self) -> str:
        """Get host identifier (peer ID)."""
        return str(self.peer_id) if self.peer_id else "unknown"
    
    def get_members(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.connected_peers)
    
    async def cleanup(self):
        """Cleanup cluster resources."""
        logger.info("Cleaning up cluster...")
        # Cleanup is handled by the context manager in start()
        logger.info("✓ Cluster cleaned up")

