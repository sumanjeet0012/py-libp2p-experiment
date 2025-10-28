#!/usr/bin/env python3
"""Main entry point for Canteen Python implementation."""
import logging
import signal
import sys
import argparse
import trio

from config import Config
from cluster import CanteenCluster
from scheduler import CanteenScheduler
from web_server import start_web_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CanteenNode:
    """Main Canteen node orchestrator."""
    
    def __init__(self):
        """Initialize the node."""
        self.config = Config()
        self.cluster = None
        self.scheduler = None
        self.shutdown_event = trio.Event()
    
    async def start(self):
        """Start all services."""
        logger.info("Starting Canteen node...")
        logger.info("")
        
        # Print configuration
        self.config.print_config()
        
        # Create cluster instance (don't start yet)
        self.cluster = CanteenCluster(
            port=self.config.p2p_port,
            namespace=self.config.mdns_service_name
        )
        
        # Run all services in nursery
        async with trio.open_nursery() as nursery:
            # Start cluster (P2P with mDNS) - runs until cancelled
            nursery.start_soon(self.cluster.start)
            
            # Wait for cluster to be ready with valid peer_id
            logger.info("Waiting for cluster to be ready...")
            await self.cluster.ready_event.wait()
            logger.info("✓ Cluster is ready, initializing scheduler...")
            
            # Create scheduler (Web3 + Docker)
            self.scheduler = CanteenScheduler(
                cluster=self.cluster,
                contract_address=self.config.contract_address,
                provider_url=self.config.blockchain_provider,
                private_key=self.config.private_key,
                memory_mb=self.config.memory_mb,
                node_port=self.config.p2p_port
            )
            
            # Initialize scheduler
            await self.scheduler.initialize()
            
            # Set scheduler reference in cluster (for P2P deployment protocol)
            self.cluster.set_scheduler(self.scheduler)
            logger.info("✓ Cluster now has scheduler reference for P2P deployments")
            
            # Start web server (in separate thread) - after scheduler is ready
            start_web_server(self.cluster, self.scheduler, self.config.web_api_port)
            logger.info("")
            
            logger.info("")
            logger.info("=" * 50)
            logger.info("🚀 Canteen Node is READY!")
            logger.info("=" * 50)
            logger.info("")
            

            # Scheduler polling loop
            nursery.start_soon(
                self.scheduler.poll_loop,
                self.config.scheduler_poll_interval
            )
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel all tasks
            nursery.cancel_scope.cancel()
    
    async def cleanup(self):
        """Cleanup all resources."""
        logger.info("")
        logger.info("=" * 50)
        logger.info("Shutting down Canteen node...")
        logger.info("=" * 50)
        
        try:
            if self.scheduler:
                await self.scheduler.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up scheduler: {e}")
        
        try:
            if self.cluster:
                await self.cluster.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up cluster: {e}")
        
        logger.info("✓ Shutdown complete")


async def main():
    """Main entry point."""
    node = CanteenNode()
    
    try:
        async with trio.open_nursery() as nursery:
            # Start signal handler
            async def handle_signals():
                with trio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signal_receiver:
                    async for sig in signal_receiver:
                        logger.info(f"Received signal {sig}, shutting down...")
                        node.shutdown_event.set()
                        nursery.cancel_scope.cancel()
                        return
            
            nursery.start_soon(handle_signals)
            nursery.start_soon(node.start)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await node.cleanup()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Canteen Python Node with FHE')
    parser.add_argument('--memory', type=int, default=4,
                        help='Available memory in GB (default: 4)')
    parser.add_argument('--port', type=int, default=5000,
                        help='P2P port number (default: 5000)')
    args = parser.parse_args()
    
    # Override config with command-line args (convert GB to MB)
    import os
    os.environ['MEMORY_MB'] = str(args.memory * 1024)
    os.environ['P2P_PORT'] = str(args.port)
    
    try:
        trio.run(main)
    except KeyboardInterrupt:
        logger.info("Exiting...")
    sys.exit(0)
