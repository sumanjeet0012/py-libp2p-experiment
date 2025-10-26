"""
FHE Credit Score Client
Encrypts financial data and sends to server for private computation.
"""

import requests
import pickle
import base64
import sys
from concrete.fhe.compilation.value import Value


class CreditScoreClient:
    """Client for interacting with FHE Credit Score Server."""
    
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url.rstrip('/')
        self.circuit = None
    
    def check_health(self):
        """Check if server is healthy and ready."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            data = response.json()
            print(f"✓ Server status: {data['status']}")
            print(f"  Circuit ready: {data['ready']}")
            return data['ready']
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
    
    def get_info(self):
        """Get server information."""
        try:
            response = requests.get(f"{self.server_url}/info")
            return response.json()
        except Exception as e:
            print(f"❌ Error getting server info: {e}")
            return None
    
    def compile_circuit_locally(self):
        """Compile the FHE circuit locally to get encryption/decryption keys."""
        print("\n[CLIENT] Compiling FHE circuit locally...")
        print("[CLIENT] (This gives us encryption/decryption keys)")
        
        # Import here to avoid dependency if not needed
        from concrete import fhe
        import numpy as np
        
        def credit_score_function(debt_to_income_ratio, credit_months, payment_score):
            score = 300
            dti_points = 200 - (debt_to_income_ratio * 2)
            history_points = credit_months * 2
            payment_points = payment_score + 50
            score = score + dti_points + history_points + payment_points
            score = score - ((score > 850) * (score - 850))
            score = score + ((score < 300) * (300 - score))
            return score
        
        inputset = [
            (
                np.random.randint(0, 101),
                np.random.randint(0, 101),
                np.random.randint(0, 101),
            )
            for _ in range(20)
        ]
        
        configuration = fhe.Configuration(
            enable_unsafe_features=True,
            use_insecure_key_cache=True,
            insecure_key_cache_location="/tmp/fhe_keys_client"
        )
        
        compiler = fhe.Compiler(
            credit_score_function,
            {
                "debt_to_income_ratio": "encrypted",
                "credit_months": "encrypted",
                "payment_score": "encrypted"
            }
        )
        
        self.circuit = compiler.compile(inputset, configuration=configuration)
        self.circuit.keygen()
        
        print("[CLIENT] ✓ Circuit compiled!")
        print("[CLIENT] ✓ Keys generated!")
        return self.circuit
    
    def encrypt_data(self, salary, loan_amount, credit_history_months, payment_delays):
        """Encrypt financial data."""
        if self.circuit is None:
            raise ValueError("Circuit not compiled. Call compile_circuit_locally() first.")
        
        # Convert to 0-100 scales (same as server)
        dti = min(100, int((loan_amount / max(salary, 1)) * 100))
        credit_score_input = min(100, int((credit_history_months / 60) * 100))
        payment_score_input = max(0, 100 - (payment_delays * 10))
        
        print(f"\n[CLIENT] Encrypting financial data...")
        print(f"  Salary: ${salary:,}")
        print(f"  Loan: ${loan_amount:,}")
        print(f"  Credit History: {credit_history_months} months")
        print(f"  Payment Delays: {payment_delays}")
        print(f"\n  Normalized: DTI={dti}, Credit={credit_score_input}, Payment={payment_score_input}")
        
        # Encrypt
        encrypted_inputs = self.circuit.encrypt(dti, credit_score_input, payment_score_input)
        
        # Serialize each encrypted value in the tuple  
        if isinstance(encrypted_inputs, tuple):
            serialized_values = [val.serialize() for val in encrypted_inputs]
            encrypted_bytes = pickle.dumps(serialized_values)
        else:
            encrypted_bytes = encrypted_inputs.serialize()
        
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        
        print("[CLIENT] ✓ Data encrypted!")
        return encrypted_b64
    
    def compute_score(self, encrypted_data):
        """Send encrypted data to server for computation."""
        print(f"\n[CLIENT] Sending encrypted data to server...")
        print("[CLIENT] (Server will not see actual values)")
        
        try:
            response = requests.post(
                f"{self.server_url}/compute",
                json={"encrypted_data": encrypted_data},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    print("[CLIENT] ✓ Server computed successfully!")
                    return data['encrypted_result']
                else:
                    print(f"[CLIENT] ❌ Server error: {data.get('message')}")
                    return None
            else:
                print(f"[CLIENT] ❌ Server returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[CLIENT] ❌ Error communicating with server: {e}")
            return None
    
    def decrypt_result(self, encrypted_result_b64):
        """Decrypt the result from server."""
        if self.circuit is None:
            raise ValueError("Circuit not compiled.")
        
        print(f"\n[CLIENT] Decrypting result...")
        
        # Decode and deserialize the encrypted result
        result_bytes = base64.b64decode(encrypted_result_b64)
        encrypted_result = Value.deserialize(result_bytes)
        
        # Decrypt
        score = self.circuit.decrypt(encrypted_result)
        
        print(f"[CLIENT] ✓ Your credit score: {score}")
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
    
    def calculate_credit_score(self, salary, loan_amount, credit_history_months, payment_delays):
        """Complete workflow: encrypt, send, compute, decrypt."""
        print("\n" + "="*70)
        print(" "*15 + "PRIVACY-PRESERVING CREDIT SCORE")
        print("="*70)
        
        # 1. Encrypt data
        encrypted_data = self.encrypt_data(salary, loan_amount, credit_history_months, payment_delays)
        
        # 2. Send to server for computation
        encrypted_result = self.compute_score(encrypted_data)
        
        if encrypted_result is None:
            print("\n❌ Failed to compute score")
            return None
        
        # 3. Decrypt result
        score = self.decrypt_result(encrypted_result)
        rating = self.get_rating(score)
        
        # 4. Display result
        print("\n" + "="*70)
        print("FINAL RESULT")
        print("="*70)
        print(f"Credit Score: {score}")
        print(f"Rating: {rating}")
        print("\n✓ Privacy preserved - server never saw your actual data!")
        print("="*70 + "\n")
        
        return score


def main():
    """Example usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='FHE Credit Score Client')
    parser.add_argument('--server', default='http://localhost:5000', help='Server URL')
    parser.add_argument('--salary', type=int, default=60000, help='Annual salary')
    parser.add_argument('--loan', type=int, default=15000, help='Loan amount')
    parser.add_argument('--history', type=int, default=48, help='Credit history (months)')
    parser.add_argument('--delays', type=int, default=1, help='Payment delays')
    
    args = parser.parse_args()
    
    # Initialize client
    client = CreditScoreClient(args.server)
    
    # Check server health
    print(f"Connecting to: {args.server}")
    if not client.check_health():
        print("\n❌ Server not ready. Make sure the server is running.")
        sys.exit(1)
    
    # Compile circuit locally
    client.compile_circuit_locally()
    
    # Calculate credit score
    client.calculate_credit_score(
        salary=args.salary,
        loan_amount=args.loan,
        credit_history_months=args.history,
        payment_delays=args.delays
    )


if __name__ == "__main__":
    main()
