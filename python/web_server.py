"""Web server for health status endpoint."""
import logging
import threading
from flask import Flask, jsonify

logger = logging.getLogger(__name__)


def start_web_server(cluster, port: int):
    """Start Flask web server for health checks.
    
    Args:
        cluster: CanteenCluster instance
        port: Port to listen on
    """
    app = Flask(__name__)
    
    # Disable Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    
    @app.route('/')
    @app.route('/cluster')
    def cluster_info():
        """Get cluster information."""
        host = cluster.get_host()
        members = cluster.get_members()
        
        # Combine host and members
        all_members = [host] + members
        
        return jsonify({
            'members': all_members,
            'self': host,
            'peers': members,
            'peer_count': len(members)
        })
    
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
