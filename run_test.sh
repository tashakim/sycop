#!/bin/bash
# Quick test run with 3 scenarios

set -e

echo "=========================================="
echo "Test Run: 3 scenarios × 6 turns × 3 conditions"
echo "=========================================="
echo ""

# Check API key
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "❌ ERROR: OPENAI_API_KEY not set and .env not found"
        exit 1
    fi
fi

echo "✓ API key configured"
echo ""

# Run test
echo "Starting test run..."
sycop all --config configs/run_test.yaml

echo ""
echo "=========================================="
echo "✓ Test complete!"
echo "=========================================="
echo ""
echo "Check outputs:"
echo "  - Run folder: runs/<run_id>/"
echo "  - Report: report/assets/"
echo ""

