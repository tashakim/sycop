#!/usr/bin/env python3
"""Compute agreement between automated and human audit labels."""

import csv
import json
import sys
from pathlib import Path
import numpy as np

def compute_audit_agreement(audit_file: Path, output_path: Path):
    """Compute agreement statistics from audit CSV."""
    rows = []
    with open(audit_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    # Filter to rows with human labels
    completed = [r for r in rows if r.get('human_endorses_premise') and r.get('human_correction_strength')]
    
    if not completed:
        print("No completed audit rows found. Fill in human_endorses_premise and human_correction_strength columns.")
        return
    
    # Agreement on endorsement
    endorsement_agreements = []
    for row in completed:
        auto = int(row['auto_endorses_premise'])
        human = int(row['human_endorses_premise'])
        endorsement_agreements.append(1 if auto == human else 0)
    
    endorsement_agreement_rate = np.mean(endorsement_agreements) if endorsement_agreements else 0
    
    # Correction strength agreement
    correction_errors = []
    for row in completed:
        auto = int(row['auto_correction_strength'])
        human = int(row['human_correction_strength'])
        correction_errors.append(abs(auto - human))
    
    mae_correction = np.mean(correction_errors) if correction_errors else None
    
    # Disagreement analysis
    disagreements = []
    for row in completed:
        auto = int(row['auto_endorses_premise'])
        human = int(row['human_endorses_premise'])
        if auto != human:
            disagreements.append({
                'scenario': row['scenario_id'],
                'condition': row['condition'],
                'turn': row['turn_idx'],
                'auto': auto,
                'human': human,
                'notes': row.get('notes', ''),
            })
    
    results = {
        'n_audited': len(completed),
        'endorsement_agreement_rate': float(endorsement_agreement_rate),
        'mae_correction_strength': float(mae_correction) if mae_correction is not None else None,
        'n_disagreements': len(disagreements),
        'disagreement_rate': len(disagreements) / len(completed) if completed else 0,
        'disagreements': disagreements[:10],  # Sample
    }
    
    # Save
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("Audit Agreement Analysis:")
    print("=" * 70)
    print(f"Turns audited: {len(completed)}")
    print(f"Endorsement agreement: {endorsement_agreement_rate:.1%}")
    print(f"Correction strength MAE: {mae_correction:.2f}" if mae_correction else "Correction strength MAE: N/A")
    print(f"Disagreements: {len(disagreements)} ({len(disagreements)/len(completed):.1%})" if completed else "Disagreements: N/A")
    
    if disagreements:
        print("\nSample disagreements:")
        for d in disagreements[:5]:
            print(f"  {d['scenario']} ({d['condition']}, turn {d['turn']}): auto={d['auto']}, human={d['human']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("report/assets/audit_agreement.json"))
    args = parser.parse_args()
    
    compute_audit_agreement(args.audit_file, args.output)

