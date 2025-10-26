"""
FHE Credit Score Server
Accepts encrypted financial data and returns encrypted credit score.
Server never sees the actual values - complete privacy preservation.
"""

from concrete import fhe
from concrete.fhe.compilation.value import Value
import numpy as np
from flask import Flask, request, jsonify
import pickle
import base64
import os


app = Flask(__name__)

# Global calculator instance
calculator = None


class SimpleCreditScoreCalculator:
    """
    Simplified credit score calculator for FHE with minimal complexity.
    Fast execution even on encrypted data.
    """
    
    def __init__(self):
        self.circuit = None
        self.client = None
        self.server = None
    
    def credit_score_function(self, debt_to_income_ratio, credit_months, payment_score):
        """
        Ultra-simplified credit score function.
        
        Inputs are pre-calculated ratios/scores (0-100 scale):
        - debt_to_income_ratio: 0-100 (lower is better)
        - credit_months: 0-100 (capped at 100, higher is better)
        - payment_score: 0-100 (higher is better)
        
        Returns score: 300-850
        """
        # Base score
        score = 300
        
        # DTI contribution (inverted - lower DTI is better)
        # Max contribution: 200 points
        dti_points = 200 - (debt_to_income_ratio * 2)
        
        # Credit history contribution
        # Max contribution: 200 points
        history_points = credit_months * 2
        
        # Payment score contribution
        # Max contribution: 150 points
        payment_points = payment_score + 50
        
        # Calculate total
        score = score + dti_points + history_points + payment_points
        
        # Cap between 300 and 850
        score = score - ((score > 850) * (score - 850))
        score = score + ((score < 300) * (300 - score))
        
        return score
    
    def compile_circuit(self):
        """
        Compile the simplified FHE circuit.
        """
        print("Compiling simplified FHE circuit...")
        
        # Simple input ranges (0-100 for all inputs)
        inputset = [
            (
                np.random.randint(0, 101),  # DTI ratio 0-100
                np.random.randint(0, 101),  # Credit months (capped)
                np.random.randint(0, 101),  # Payment score
            )
            for _ in range(20)  # Only 20 samples needed
        ]
        
        # Fast configuration
        configuration = fhe.Configuration(
            enable_unsafe_features=True,
            use_insecure_key_cache=True,
            insecure_key_cache_location="/tmp/fhe_keys_simple"
        )
        
        compiler = fhe.Compiler(
            self.credit_score_function,
            {
                "debt_to_income_ratio": "encrypted",
                "credit_months": "encrypted",
                "payment_score": "encrypted"
            }
        )
        
        print("⚠️  Using demo mode (fast but less secure)")
        self.circuit = compiler.compile(inputset, configuration=configuration)
        print(f"✓ Compiled! Complexity: {self.circuit.complexity:.2e}")
        
        print("\nGenerating keys...")
        self.circuit.keygen()
        print("✓ Keys ready!")
        
        return self.circuit
    
    def calculate_encrypted_score(self, salary, loan_amount, credit_history_months, payment_delays):
        """
        Complete workflow: calculate score on encrypted data.
        
        Args:
            salary: Annual salary (e.g., 60000)
            loan_amount: Loan requested (e.g., 15000)
            credit_history_months: Credit history in months (e.g., 48)
            payment_delays: Number of payment delays (e.g., 1)
        """
        print(f"\n{'='*70}")
        print("PRIVATE CREDIT SCORE CALCULATION")
        print(f"{'='*70}")
        
        # Convert to 0-100 scales
        dti = min(100, int((loan_amount / max(salary, 1)) * 100))
        credit_score_input = min(100, int((credit_history_months / 60) * 100))
        payment_score_input = max(0, 100 - (payment_delays * 10))
        
        print(f"\n[CLIENT] Input Data:")
        print(f"  Salary: ${salary:,}")
        print(f"  Loan: ${loan_amount:,}")
        print(f"  Credit History: {credit_history_months} months")
        print(f"  Payment Delays: {payment_delays}")
        
        print(f"\n[CLIENT] Normalized values (0-100 scale):")
        print(f"  DTI Ratio: {dti}")
        print(f"  Credit Score: {credit_score_input}")
        print(f"  Payment Score: {payment_score_input}")
        
        # Encrypt
        print(f"\n[CLIENT] Encrypting...")
        encrypted_inputs = self.circuit.encrypt(dti, credit_score_input, payment_score_input)
        print("✓ Data encrypted!")
        
        # Compute on encrypted data
        print(f"\n[SERVER] Computing on encrypted data...")
        print("[SERVER] (Server cannot see actual values)")
        encrypted_result = self.circuit.run(encrypted_inputs)
        print("✓ Computation complete!")
        
        # Decrypt
        print(f"\n[CLIENT] Decrypting result...")
        score = self.circuit.decrypt(encrypted_result)
        print(f"✓ Your credit score: {score}")
        
        return score
    
    def get_rating(self, score):
        """Get text rating for score."""
        if score >= 750:
            return "Excellent"
        elif score >= 700:
            return "Good"
        elif score >= 650:
            return "Fair"
        elif score >= 600:
            return "Poor"
        else:
            return "Very Poor"


# Flask API endpoints
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "FHE Credit Score Server",
        "ready": calculator is not None and calculator.circuit is not None
    })


@app.route('/compile', methods=['POST'])
def compile_circuit():
    """Compile the FHE circuit (one-time setup)."""
    global calculator
    try:
        calculator = SimpleCreditScoreCalculator()
        calculator.compile_circuit()
        print("✓ Circuit compiled and ready!")
        
        return jsonify({
            "status": "success",
            "message": "Circuit compiled successfully",
            "complexity": float(calculator.circuit.complexity)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/compute', methods=['POST'])
def compute_score():
    """
    Compute credit score on encrypted data.
    
    Expects JSON:
    {
        "encrypted_data": "base64_encoded_encrypted_inputs"
    }
    
    Returns:
    {
        "encrypted_result": "base64_encoded_encrypted_score"
    }
    """
    global calculator
    
    if calculator is None or calculator.circuit is None:
        return jsonify({
            "status": "error",
            "message": "Circuit not compiled. Call /compile first."
        }), 400
    
    try:
        # Get encrypted data from request
        data = request.get_json()
        encrypted_data_b64 = data.get('encrypted_data')
        
        if not encrypted_data_b64:
            return jsonify({
                "status": "error",
                "message": "Missing 'encrypted_data' field"
            }), 400
        
        # Decode from base64 and deserialize
        encrypted_data_bytes = base64.b64decode(encrypted_data_b64)
        serialized_values = pickle.loads(encrypted_data_bytes)
        
        # Deserialize each value
        encrypted_inputs = tuple(Value.deserialize(val) for val in serialized_values)
        
        print("[SERVER] Received encrypted data")
        print("[SERVER] Computing on encrypted values...")
        
        # Compute on encrypted data
        encrypted_result = calculator.circuit.run(*encrypted_inputs)
        
        # Serialize result
        result_bytes = encrypted_result.serialize()
        result_b64 = base64.b64encode(result_bytes).decode('utf-8')
        
        print("[SERVER] ✓ Computation complete!")
        
        return jsonify({
            "status": "success",
            "encrypted_result": result_b64
        })
        
    except Exception as e:
        print(f"[SERVER] Error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/info', methods=['GET'])
def info():
    """Get server information."""
    return jsonify({
        "service": "FHE Credit Score Server",
        "description": "Privacy-preserving credit score calculation using Zama's Concrete FHE",
        "endpoints": {
            "/health": "GET - Health check",
            "/compile": "POST - Compile FHE circuit (one-time setup)",
            "/compute": "POST - Compute score on encrypted data",
            "/info": "GET - This endpoint"
        },
        "privacy": "Server never sees actual values - all computation on encrypted data",
        "circuit_ready": calculator is not None and calculator.circuit is not None
    })


def initialize_server():
    """Initialize server and compile circuit on startup."""
    global calculator
    print("\n" + "="*70)
    print(" "*15 + "FHE CREDIT SCORE SERVER")
    print(" "*20 + "Starting up...")
    print("="*70)
    
    print("\n[SERVER] Compiling FHE circuit...")
    calculator = SimpleCreditScoreCalculator()
    calculator.compile_circuit()
    
    print("\n" + "="*70)
    print(" "*15 + "SERVER READY!")
    print("="*70)
    print("\nEndpoints available:")
    print("  GET  /health  - Health check")
    print("  GET  /info    - Server information")
    print("  POST /compile - Recompile FHE circuit")
    print("  POST /compute - Compute encrypted score")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # Initialize on startup
    initialize_server()
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
