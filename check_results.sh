#!/bin/bash
# Quick script to check evaluation results

echo "=========================================="
echo "Results Check"
echo "=========================================="
echo ""

# Find latest run
LATEST_RUN=$(ls -t runs/ 2>/dev/null | head -1)

if [ -z "$LATEST_RUN" ]; then
    echo "❌ No runs found. Run evaluation first."
    exit 1
fi

echo "Latest run: $LATEST_RUN"
echo ""

# Check files
echo "Checking outputs..."
echo ""

if [ -f "runs/$LATEST_RUN/transcripts.jsonl" ]; then
    TRANSCRIPT_COUNT=$(wc -l < "runs/$LATEST_RUN/transcripts.jsonl")
    echo "✓ Transcripts: $TRANSCRIPT_COUNT turns"
else
    echo "✗ Transcripts missing"
fi

if [ -f "runs/$LATEST_RUN/labels.jsonl" ]; then
    LABEL_COUNT=$(wc -l < "runs/$LATEST_RUN/labels.jsonl")
    echo "✓ Labels: $LABEL_COUNT turns"
else
    echo "✗ Labels missing"
fi

if [ -f "runs/$LATEST_RUN/aggregates.json" ]; then
    echo "✓ Aggregates: Found"
    echo ""
    echo "Metrics summary:"
    python3 -c "
import json
with open('runs/$LATEST_RUN/aggregates.json') as f:
    data = json.load(f)
    for cond, metrics in data.items():
        if cond != 'baseline_vs_enforce':
            print(f'\n{cond.upper()}:')
            if 'ads' in metrics:
                ads = metrics['ads']
                print(f'  ADS: {ads[0]:.3f} [{ads[1]:.3f}, {ads[2]:.3f}]')
            if 'csd' in metrics:
                csd = metrics['csd']
                print(f'  CSD: {csd[0]:.3f} [{csd[1]:.3f}, {csd[2]:.3f}]')
            if 'nsi' in metrics:
                nsi = metrics['nsi']
                print(f'  NSI: {nsi[0]:.3f} [{nsi[1]:.3f}, {nsi[2]:.3f}]')
" 2>/dev/null || echo "  (Install python3 to view formatted metrics)"
else
    echo "✗ Aggregates missing"
fi

echo ""
if [ -f "report/assets/table1.md" ]; then
    echo "✓ Table 1: report/assets/table1.md"
    echo ""
    echo "Preview:"
    head -10 report/assets/table1.md
else
    echo "✗ Table 1 missing"
fi

echo ""
if [ -f "report/assets/fig_turn_drift.png" ]; then
    echo "✓ Plot: fig_turn_drift.png"
else
    echo "✗ Plot missing: fig_turn_drift.png"
fi

if [ -f "report/assets/fig_nsi.png" ]; then
    echo "✓ Plot: fig_nsi.png"
else
    echo "✗ Plot missing: fig_nsi.png"
fi

echo ""
echo "=========================================="

