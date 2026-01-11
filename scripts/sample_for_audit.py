#!/usr/bin/env python3
"""Systematically sample turns for human audit."""

import json
import random
import sys
from pathlib import Path
from collections import defaultdict
import csv

def sample_for_audit(run_id: str, n_samples: int, output_path: Path, stratify_by: list = None):
    """Sample turns for human audit with optional stratification."""
    run_path = Path("runs") / run_id
    
    # Load transcripts
    transcripts = []
    with open(run_path / "transcripts.jsonl") as f:
        for line in f:
            if line.strip():
                transcripts.append(json.loads(line))
    
    # Load labels
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
    
    # Group by stratification variables
    if stratify_by:
        groups = defaultdict(list)
        for t in transcripts:
            key = tuple(t.get(s, 'unknown') for s in stratify_by)
            groups[key].append(t)
        
        # Sample proportionally from each group
        sampled = []
        for group_items in groups.values():
            n_from_group = max(1, int(n_samples * len(group_items) / len(transcripts)))
            sampled.extend(random.sample(group_items, min(n_from_group, len(group_items))))
        
        # If we need more, sample randomly from remaining
        if len(sampled) < n_samples:
            remaining = [t for t in transcripts if t not in sampled]
            sampled.extend(random.sample(remaining, min(n_samples - len(sampled), len(remaining))))
        
        sampled = sampled[:n_samples]
    else:
        sampled = random.sample(transcripts, min(n_samples, len(transcripts)))
    
    # Create audit CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'scenario_id', 'condition', 'turn_idx', 'assistant_reply',
            'contested_premise', 'auto_endorses_premise', 'human_endorses_premise',
            'auto_correction_strength', 'human_correction_strength', 'notes'
        ])
        
        for t in sampled:
            key = (t['scenario_id'], t['condition'], t['turn_idx'])
            label = label_dict.get(key, {})
            
            agreement = label.get('agreement', {})
            auto_endorses = 1 if (isinstance(agreement, dict) and agreement.get('endorses_premise')) else 0
            
            correction = label.get('correction_strength', {})
            auto_correction = correction.get('score', 0) if isinstance(correction, dict) else 0
            
            writer.writerow([
                t['scenario_id'],
                t['condition'],
                t['turn_idx'],
                t['assistant'][:500],  # Truncate for CSV
                t['meta']['contested_premise'],
                auto_endorses,
                '',  # Human to fill
                auto_correction,
                '',  # Human to fill
                ''   # Human notes
            ])
    
    print(f"Sampled {len(sampled)} turns for audit")
    print(f"Saved to: {output_path}")
    print(f"\nStratification:")
    if stratify_by:
        for var in stratify_by:
            counts = defaultdict(int)
            for t in sampled:
                counts[t.get(var, 'unknown')] += 1
            print(f"  {var}: {dict(counts)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--n-samples", type=int, default=25)
    parser.add_argument("--stratify-by", nargs='+', default=['category', 'condition'])
    parser.add_argument("--output", type=Path, default=Path("report/human_audit_sample.csv"))
    args = parser.parse_args()
    
    random.seed(42)  # Reproducible sampling
    sample_for_audit(args.run_id, args.n_samples, args.output, args.stratify_by)

