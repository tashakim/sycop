#!/usr/bin/env python3
"""Analyze turn-by-turn drift patterns."""

import json
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

def analyze_turn_drift(run_id: str, output_path: Path):
    """Analyze agreement drift across turns."""
    run_path = Path("runs") / run_id
    
    # Load transcripts and labels
    transcripts = []
    with open(run_path / "transcripts.jsonl") as f:
        for line in f:
            if line.strip():
                transcripts.append(json.loads(line))
    
    labels = []
    with open(run_path / "labels.jsonl") as f:
        for line in f:
            if line.strip():
                labels.append(json.loads(line))
    
    # Index labels
    label_dict = {}
    for label in labels:
        key = (label['scenario_id'], label['condition'], label['turn_idx'])
        label_dict[key] = label
    
    # Group by condition and turn
    turn_data = defaultdict(lambda: defaultdict(list))
    
    for transcript in transcripts:
        cond = transcript['condition']
        turn_idx = transcript['turn_idx']
        key = (transcript['scenario_id'], cond, turn_idx)
        label = label_dict.get(key, {})
        
        # Agreement
        agreement = label.get('agreement', {})
        if isinstance(agreement, dict) and agreement.get('endorses_premise') is not None:
            turn_data[cond][turn_idx].append(1 if agreement['endorses_premise'] else 0)
        
        # Correction strength
        correction = label.get('correction_strength', {})
        if isinstance(correction, dict) and correction.get('score') is not None:
            turn_data[cond][f"{turn_idx}_correction"].append(correction['score'])
        
        # NSI components
        rapport = label.get('rapport_count', 0)
        epistemic = label.get('epistemic_count', 0)
        if rapport + epistemic > 0:
            nsi = rapport / (rapport + epistemic)
            turn_data[cond][f"{turn_idx}_nsi"].append(nsi)
    
    # Compute aggregates
    aggregates = {}
    for cond in ['baseline', 'log', 'enforce']:
        aggregates[cond] = {}
        
        # Agreement by turn
        agreement_by_turn = []
        for turn_idx in range(6):
            if turn_idx in turn_data[cond]:
                values = turn_data[cond][turn_idx]
                if values:
                    agreement_by_turn.append({
                        'turn': turn_idx,
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'n': len(values),
                    })
        
        aggregates[cond]['agreement_by_turn'] = agreement_by_turn
        
        # Correction strength by turn
        correction_by_turn = []
        for turn_idx in range(6):
            key = f"{turn_idx}_correction"
            if key in turn_data[cond]:
                values = turn_data[cond][key]
                if values:
                    correction_by_turn.append({
                        'turn': turn_idx,
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'n': len(values),
                    })
        
        aggregates[cond]['correction_by_turn'] = correction_by_turn
        
        # NSI by turn
        nsi_by_turn = []
        for turn_idx in range(6):
            key = f"{turn_idx}_nsi"
            if key in turn_data[cond]:
                values = turn_data[cond][key]
                if values:
                    nsi_by_turn.append({
                        'turn': turn_idx,
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'n': len(values),
                    })
        
        aggregates[cond]['nsi_by_turn'] = nsi_by_turn
        
        # Compute drift (early vs late)
        if len(agreement_by_turn) >= 3:
            early = [a['mean'] for a in agreement_by_turn[:3]]
            late = [a['mean'] for a in agreement_by_turn[-3:]]
            aggregates[cond]['drift'] = {
                'early_mean': float(np.mean(early)),
                'late_mean': float(np.mean(late)),
                'drift': float(np.mean(late) - np.mean(early)),
            }
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(aggregates, f, indent=2)
    
    # Print summary
    print("Turn-by-Turn Drift Analysis:")
    print("=" * 70)
    for cond in ['baseline', 'enforce']:
        if cond in aggregates and 'drift' in aggregates[cond]:
            drift = aggregates[cond]['drift']
            print(f"\n{cond.upper()}:")
            print(f"  Early turns (0-2): {drift['early_mean']:.2%} agreement")
            print(f"  Late turns (3-5): {drift['late_mean']:.2%} agreement")
            print(f"  Drift: {drift['drift']:.2%} change")
    
    # Compare baseline vs enforce
    if 'baseline' in aggregates and 'enforce' in aggregates:
        baseline_drift = aggregates['baseline'].get('drift', {}).get('drift', 0)
        enforce_drift = aggregates['enforce'].get('drift', {}).get('drift', 0)
        print(f"\n✓ Enforcement reduces drift:")
        print(f"  Baseline drift: {baseline_drift:.2%}")
        print(f"  Enforce drift: {enforce_drift:.2%}")
        print(f"  Reduction: {((baseline_drift - enforce_drift) / baseline_drift * 100) if baseline_drift > 0 else 0:.1f}%")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("report/assets/turn_drift_analysis.json"))
    args = parser.parse_args()
    
    analyze_turn_drift(args.run_id, args.output)

