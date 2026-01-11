#!/bin/bash
# Run full evaluation pipeline end-to-end

set -e  # Exit on error

echo "=========================================="
echo "Sycophancy Under Pressure - Full Pipeline"
echo "=========================================="
echo ""

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not set"
    echo "   Set it with: export OPENAI_API_KEY='your-key'"
    exit 1
fi

echo "API key found"
echo ""

# Check if installed
if ! command -v sycop &> /dev/null; then
    echo "Installing package..."
    pip install -e . > /dev/null 2>&1
    echo "Package installed"
fi

echo "Starting full pipeline..."
echo ""

# Run full pipeline
sycop all \
    --config configs/run_v1.yaml \
    --base-path runs \
    --out report/assets

echo ""
echo "=========================================="
echo "Pipeline complete!"
echo "=========================================="
echo ""
echo "Outputs:"
echo "  - Run folder: runs/<run_id>/"
echo "  - Report: report/assets/"
echo ""
echo "Next steps:"
echo "  1. Review report/assets/table1.md"
echo "  2. Check plots in report/assets/"
echo "  3. Sample turns for human audit"
echo "  4. Complete report template"
echo ""

