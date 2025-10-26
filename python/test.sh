#!/bin/bash

echo "========================================"
echo "  FHE Credit Score - Quick Test"
echo "========================================"
echo ""

# Check if server is running
echo "Checking if server is running..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✓ Server is running"
else
    echo "❌ Server is not running"
    echo ""
    echo "Start the server first:"
    echo "  Option 1: docker-compose up"
    echo "  Option 2: python encrypted_credit_score_simple.py"
    exit 1
fi

echo ""
echo "Getting server info..."
curl -s http://localhost:5000/info | python -m json.tool

echo ""
echo "========================================"
echo "  Running client test..."
echo "========================================"
echo ""

python client.py --salary 60000 --loan 15000 --history 48 --delays 1

echo ""
echo "========================================"
echo "✓ Test complete!"
echo "========================================"
