#!/usr/bin/env python3
"""
Check registered members in the Canteen contract and their assigned containers.
"""

import json
from web3 import Web3

# Connect to Ganache
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))

# Load contract ABI
with open('build/contracts/Canteen.json') as f:
    contract_json = json.load(f)
    contract_abi = contract_json['abi']
    networks = contract_json['networks']
    
    # Get the latest network deployment
    network_id = list(networks.keys())[-1]
    contract_address = networks[network_id]['address']

# Create contract instance
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Get account
account = w3.eth.accounts[0]

print("=" * 80)
print("CANTEEN CONTRACT MEMBER STATUS")
print("=" * 80)
print(f"Contract Address: {contract_address}")
print(f"Network ID: {network_id}")
print()

# Get total number of members
try:
    member_count = contract.functions.getMembersCount().call()
    print(f"Total Registered Members: {member_count}")
    print()
    
    if member_count == 0:
        print("No members registered yet.")
    else:
        print("-" * 80)
        print("REGISTERED MEMBERS:")
        print("-" * 80)
        
        # Iterate through all members
        for idx in range(member_count):
            host_id = contract.functions.members(idx).call()
            print(f"\n{idx + 1}. Host/Peer ID: {host_id}")
            
            # Get member details
            try:
                member_details = contract.functions.getMemberDetails(host_id).call()
                image_name = member_details[0]
                is_active = member_details[1]
                encrypted_memory = member_details[2]
                
                print(f"   Assigned Image: {image_name if image_name else 'None'}")
                print(f"   Status: {'Active' if is_active else 'Inactive'}")
                
                if encrypted_memory:
                    print(f"   Encrypted Memory: {encrypted_memory.hex()[:64]}... ({len(encrypted_memory)} bytes)")
                else:
                    print(f"   Encrypted Memory: Not set")
                
            except Exception as e:
                print(f"   Error getting member details: {e}")
        
        print()
        print("-" * 80)
        print("IMAGE DEPLOYMENTS:")
        print("-" * 80)
        
        # Get all images
        try:
            image_count = contract.functions.getImagesCount().call()
            if image_count == 0:
                print("\nNo images deployed yet.")
            else:
                for idx in range(image_count):
                    image_name = contract.functions.images(idx).call()
                    image_details = contract.functions.getImageDetails(image_name).call()
                    replicas = image_details[0]
                    deployed = image_details[1]
                    is_active = image_details[2]
                    
                    print(f"\n{idx + 1}. {image_name}")
                    print(f"   Requested Replicas: {replicas}")
                    print(f"   Deployed: {deployed}")
                    print(f"   Status: {'Active' if is_active else 'Inactive'}")
        except Exception as e:
            print(f"\nError getting images: {e}")
        
except Exception as e:
    print(f"Error accessing contract: {e}")
    print("\nMake sure:")
    print("1. Ganache is running on http://127.0.0.1:7545")
    print("2. Contract has been deployed (run: truffle migrate)")
    print("3. Contract ABI is up to date in build/contracts/Canteen.json")

print()
print("=" * 80)
