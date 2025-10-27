"""Web server for health status endpoint."""
import logging
import threading
from flask import Flask, jsonify

logger = logging.getLogger(__name__)


def start_web_server(cluster, scheduler, port: int):
    """Start Flask web server for health checks.
    
    Args:
        cluster: CanteenCluster instance
        scheduler: CanteenScheduler instance (for contract access)
        port: Port to listen on
    """
    app = Flask(__name__)
    
    # Disable Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    
    @app.route('/')
    @app.route('/cluster')
    def cluster_info():
        """Get cluster information from smart contract (single source of truth)."""
        try:
            # Get self
            host = cluster.get_host()
            
            # Get all members from contract (single source of truth)
            contract_members = scheduler.get_contract_members()
            
            # Get P2P connected peers (for connection status)
            connected_peers = cluster.get_connected_peers()
            
            # Build member details with connection status
            member_details = []
            for member_id in contract_members:
                member_details.append({
                    'peer_id': member_id,
                    'connected': member_id in connected_peers or member_id == host,
                    'is_self': member_id == host
                })
            
            return jsonify({
                'members': contract_members,  # All registered members from contract
                'member_details': member_details,  # With connection status
                'self': host,
                'connected_peers': connected_peers,  # Actually connected via P2P
                'total_members': len(contract_members),
                'connected_count': len(connected_peers)
            })
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return jsonify({
                'error': str(e),
                'members': [],
                'self': cluster.get_host()
            }), 500
    
    @app.route('/health')
    def health():
        """Simple health check."""
        return jsonify({
            'status': 'healthy',
            'peer_id': cluster.get_host()
        })
    
    # Enable CORS
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    def run_server():
        """Run Flask server."""
        try:
            logger.info(f"Starting web server on port {port}...")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Web server error: {e}")
    
    # Start server in separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    logger.info(f"✓ Web server started on http://0.0.0.0:{port}")
    logger.info(f"  Health check: http://localhost:{port}/health")
    logger.info(f"  Cluster info: http://localhost:{port}/cluster")
