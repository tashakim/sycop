#!/usr/bin/env python3
"""Analyze metrics by category to extract category-specific insights."""

import json
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

def analyze_by_category(run_id: str, output_path: Path):
    """Analyze metrics grouped by category."""
    run_path = Path("runs") / run_id
    
    # Load metrics
    with open(run_path / "metrics.json") as f:
        metrics = json.load(f)
    
    # Load transcripts for category info
    transcripts = []
    with open(run_path / "transcripts.jsonl") as f:
        for line in f:
            if line.strip():
                transcripts.append(json.loads(line))
    
    # Map scenario IDs to categories
    scenario_categories = {}
    for t in transcripts:
        if t['scenario_id'] not in scenario_categories:
            scenario_categories[t['scenario_id']] = t['category']
    
    # Group metrics by category
    category_data = defaultdict(lambda: {'baseline': [], 'log': [], 'enforce': []})
    
    for key, m in metrics.items():
        # Parse key like "FP_001_baseline"
        parts = key.rsplit('_', 1)
        if len(parts) == 2:
            scenario_key = parts[0]
            condition = parts[1]
            
            # Find category
            category = None
            for sid, cat in scenario_categories.items():
                if scenario_key.startswith(sid.split('_')[0]):
                    category = cat
                    break
            
            if category and condition in category_data[category]:
                if m.get('ads') is not None:
                    category_data[category][condition].append({
                        'ads': m['ads'],
                        'csd': m.get('csd'),
                        'nsi': m.get('nsi'),
                        'scenario': scenario_key,
                    })
    
    # Compute category-level aggregates
    category_aggregates = {}
    for category, data in category_data.items():
        category_aggregates[category] = {}
        
        for condition in ['baseline', 'log', 'enforce']:
            if data[condition]:
                ads_values = [m['ads'] for m in data[condition] if m['ads'] is not None]
                csd_values = [m['csd'] for m in data[condition] if m['csd'] is not None]
                nsi_values = [m['nsi'] for m in data[condition] if m['nsi'] is not None]
                
                category_aggregates[category][condition] = {
                    'n': len(data[condition]),
                    'ads': {
                        'mean': float(np.mean(ads_values)) if ads_values else None,
                        'std': float(np.std(ads_values)) if ads_values else None,
                    } if ads_values else None,
                    'csd': {
                        'mean': float(np.mean(csd_values)) if csd_values else None,
                        'std': float(np.std(csd_values)) if csd_values else None,
                    } if csd_values else None,
                    'nsi': {
                        'mean': float(np.mean(nsi_values)) if nsi_values else None,
                        'std': float(np.std(nsi_values)) if nsi_values else None,
                    } if nsi_values else None,
                }
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(category_aggregates, f, indent=2)
    
    # Print summary
    print("Category-Level Analysis:")
    print("=" * 70)
    for category, data in category_aggregates.items():
        print(f"\n{category.upper()}:")
        for condition in ['baseline', 'enforce']:
            if condition in data and data[condition].get('ads'):
                ads_mean = data[condition]['ads']['mean']
                n = data[condition]['n']
                print(f"  {condition}: ADS={ads_mean:.4f} (n={n})")
        
        # Compute reduction
        if 'baseline' in data and 'enforce' in data:
            baseline_ads = data['baseline'].get('ads', {}).get('mean')
            enforce_ads = data['enforce'].get('ads', {}).get('mean')
            if baseline_ads and enforce_ads and baseline_ads > 0:
                reduction = ((baseline_ads - enforce_ads) / baseline_ads) * 100
                print(f"  Reduction: {reduction:.1f}%")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("report/assets/category_breakdown.json"))
    args = parser.parse_args()
    
    analyze_by_category(args.run_id, args.output)

