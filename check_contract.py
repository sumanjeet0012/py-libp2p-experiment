#!/usr/bin/env python3
"""Check contract state - view registered members and images."""
import json
import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Connect to blockchain
provider_url = os.getenv('BLOCKCHAIN_PROVIDER', 'http://localhost:7545')
contract_address = os.getenv('CONTRACT_ADDRESS', '0x94b304c25CC9Ac21Fd6aa210eBE45c86846a3cc5')

w3 = Web3(Web3.HTTPProvider(provider_url))

if not w3.is_connected():
    print("❌ Failed to connect to blockchain at", provider_url)
    exit(1)

print("✅ Connected to blockchain")
print()

# Load contract
with open('build/contracts/Canteen.json') as f:
    contract_json = json.load(f)
    contract = w3.eth.contract(
        address=contract_address,
        abi=contract_json['abi']
    )

print("=" * 60)
print("CANTEEN CONTRACT STATE")
print("=" * 60)
print(f"Contract Address: {contract_address}")
print()

# Get members
print("📋 REGISTERED MEMBERS:")
print("-" * 60)
try:
    member_count = 0
    index = 0
    while True:
        try:
            member_host = contract.functions.members(index).call()
            if member_host:
                details = contract.functions.getMemberDetails(member_host).call()
                image_name = details[0]
                is_active = details[1]
                
                status = "🟢 Active" if is_active else "🔴 Inactive"
                image_display = f"'{image_name}'" if image_name else "None"
                
                print(f"{index + 1}. {status}")
                print(f"   Host: {member_host}")
                print(f"   Image: {image_display}")
                print()
                
                member_count += 1
                index += 1
            else:
                break
        except Exception:
            break
    
    if member_count == 0:
        print("   No members registered yet")
        print()
except Exception as e:
    print(f"   Error reading members: {e}")
    print()

# Get images
print("🐳 REGISTERED IMAGES:")
print("-" * 60)
try:
    image_count = 0
    index = 0
    while True:
        try:
            image_name = contract.functions.images(index).call()
            if image_name:
                details = contract.functions.getImageDetails(image_name).call()
                replicas = details[0]
                deployed = details[1]
                is_active = details[2]
                
                status = "🟢 Active" if is_active else "🔴 Inactive"
                progress = f"{deployed}/{replicas}"
                
                print(f"{index + 1}. {status}")
                print(f"   Name: {image_name}")
                print(f"   Deployed: {progress}")
                print()
                
                image_count += 1
                index += 1
            else:
                break
        except Exception:
            break
    
    if image_count == 0:
        print("   No images registered yet")
        print()
except Exception as e:
    print(f"   Error reading images: {e}")
    print()

print("=" * 60)
print()

# Summary
print("SUMMARY:")
print(f"  Total Members: {member_count if 'member_count' in locals() else 0}")
print(f"  Total Images: {image_count if 'image_count' in locals() else 0}")
print()
