"""Web server for health status endpoint."""
import logging
import threading
from flask import Flask, jsonify, request

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
    
    @app.route('/deploy', methods=['POST'])
    def deploy():
        """Deploy a Docker image with specified replicas.
        
        Request JSON:
            {
                "image": "nginx:latest",
                "replicas": 3
            }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
            image_name = data.get('image')
            replicas = data.get('replicas', 1)
            
            if not image_name:
                return jsonify({'success': False, 'error': 'Image name is required'}), 400
            
            if not isinstance(replicas, int) or replicas < 1:
                return jsonify({'success': False, 'error': 'Replicas must be a positive integer'}), 400
            
            # Get all members from contract
            contract_members = scheduler.get_contract_members()
            
            if len(contract_members) == 0:
                return jsonify({'success': False, 'error': 'No members in cluster'}), 400
            
            # Limit replicas to available members
            actual_replicas = min(replicas, len(contract_members))
            
            # Select nodes for deployment (round-robin style)
            # For simplicity, take the first N members
            selected_nodes = contract_members[:actual_replicas]
            
            # Assign image to selected nodes via contract
            assigned = []
            failed = []
            
            for node_id in selected_nodes:
                try:
                    tx_hash = scheduler.contract.functions.setImage(node_id, image_name).transact({
                        'from': scheduler.account,
                        'gas': 300000
                    })
                    receipt = scheduler.w3.eth.wait_for_transaction_receipt(tx_hash)
                    
                    if receipt.status == 1:
                        assigned.append(node_id)
                        logger.info(f"Assigned {image_name} to {node_id[:10]}...")
                    else:
                        failed.append(node_id)
                        logger.error(f"Failed to assign to {node_id[:10]}...")
                        
                except Exception as e:
                    logger.error(f"Error assigning to {node_id}: {e}")
                    failed.append(node_id)
            
            return jsonify({
                'success': len(assigned) > 0,
                'image': image_name,
                'requested_replicas': replicas,
                'actual_replicas': len(assigned),
                'assigned_nodes': assigned,
                'failed_nodes': failed,
                'total_members': len(contract_members)
            })
            
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/undeploy', methods=['POST'])
    def undeploy():
        """Remove a Docker image deployment.
        
        Request JSON:
            {
                "image": "nginx:latest"
            }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
            image_name = data.get('image')
            
            if not image_name:
                return jsonify({'success': False, 'error': 'Image name is required'}), 400
            
            # Get all members and find those running this image
            contract_members = scheduler.get_contract_members()
            removed = []
            failed = []
            
            for node_id in contract_members:
                try:
                    # Get current image for this node
                    details = scheduler.contract.functions.getMemberDetails(node_id).call()
                    current_image = details[0]
                    
                    if current_image == image_name:
                        # Remove image assignment (set to empty string)
                        tx_hash = scheduler.contract.functions.setImage(node_id, "").transact({
                            'from': scheduler.account,
                            'gas': 300000
                        })
                        receipt = scheduler.w3.eth.wait_for_transaction_receipt(tx_hash)
                        
                        if receipt.status == 1:
                            removed.append(node_id)
                            logger.info(f"Removed {image_name} from {node_id[:10]}...")
                        else:
                            failed.append(node_id)
                            
                except Exception as e:
                    logger.error(f"Error removing from {node_id}: {e}")
                    failed.append(node_id)
            
            return jsonify({
                'success': len(removed) > 0,
                'image': image_name,
                'removed_from': removed,
                'failed': failed,
                'total_removed': len(removed)
            })
            
        except Exception as e:
            logger.error(f"Undeployment error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
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
    logger.info(f"  Deploy image: POST http://localhost:{port}/deploy")
    logger.info(f"  Undeploy image: POST http://localhost:{port}/undeploy")
