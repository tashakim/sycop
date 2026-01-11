#!/usr/bin/env python3
"""Analyze intervention patterns and effectiveness."""

import json
import sys
from pathlib import Path
import numpy as np

def analyze_interventions(run_id: str, output_path: Path):
    """Analyze when/why interventions occur and their effectiveness."""
    run_path = Path("runs") / run_id
    
    # Load metrics
    with open(run_path / "metrics.json") as f:
        metrics = json.load(f)
    
    # Load transcripts
    transcripts = []
    with open(run_path / "transcripts.jsonl") as f:
        for line in f:
            if line.strip():
                transcripts.append(json.loads(line))
    
    # Find enforce condition scenarios with interventions
    intervention_data = []
    
    for key, m in metrics.items():
        if 'enforce' in key and 'intervention_rate' in m:
            intervention_rate = m['intervention_rate']
            if intervention_rate > 0:
                # Get scenario ID
                scenario_key = key.rsplit('_', 1)[0]
                
                # Find baseline for comparison
                baseline_key = f"{scenario_key}_baseline"
                baseline_ads = metrics.get(baseline_key, {}).get('ads')
                enforce_ads = m.get('ads')
                
                # Get category
                category = None
                for t in transcripts:
                    if t['scenario_id'] == scenario_key.split('_')[0] + '_' + scenario_key.split('_')[1] if '_' in scenario_key else scenario_key:
                        category = t['category']
                        break
                
                intervention_data.append({
                    'scenario': scenario_key,
                    'category': category,
                    'intervention_rate': intervention_rate,
                    'baseline_ads': baseline_ads,
                    'enforce_ads': enforce_ads,
                    'ads_reduction': (baseline_ads - enforce_ads) if (baseline_ads and enforce_ads) else None,
                })
    
    # Analyze patterns
    analysis = {
        'total_scenarios_with_interventions': len(intervention_data),
        'average_intervention_rate': float(np.mean([d['intervention_rate'] for d in intervention_data])) if intervention_data else 0,
        'interventions_by_category': {},
        'intervention_effectiveness': {},
    }
    
    # Group by category
    by_category = {}
    for item in intervention_data:
        cat = item['category'] or 'unknown'
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)
    
    for cat, items in by_category.items():
        analysis['interventions_by_category'][cat] = {
            'count': len(items),
            'avg_intervention_rate': float(np.mean([i['intervention_rate'] for i in items])),
            'avg_ads_reduction': float(np.mean([i['ads_reduction'] for i in items if i['ads_reduction'] is not None])),
        }
    
    # Effectiveness analysis
    if intervention_data:
        ads_reductions = [d['ads_reduction'] for d in intervention_data if d['ads_reduction'] is not None]
        intervention_rates = [d['intervention_rate'] for d in intervention_data]
        
        if ads_reductions:
            # Correlation
            correlation = np.corrcoef(intervention_rates[:len(ads_reductions)], ads_reductions)[0, 1] if len(ads_reductions) > 1 else 0
            
            analysis['intervention_effectiveness'] = {
                'correlation_intervention_vs_reduction': float(correlation) if not np.isnan(correlation) else None,
                'avg_reduction_with_intervention': float(np.mean(ads_reductions)),
                'scenarios_benefiting': sum(1 for r in ads_reductions if r > 0),
            }
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Print summary
    print("Intervention Pattern Analysis:")
    print("=" * 70)
    print(f"\nTotal scenarios with interventions: {analysis['total_scenarios_with_interventions']}")
    print(f"Average intervention rate: {analysis['average_intervention_rate']:.2%}")
    
    print("\nBy Category:")
    for cat, data in analysis['interventions_by_category'].items():
        print(f"  {cat}: {data['count']} scenarios, {data['avg_intervention_rate']:.1%} avg rate")
    
    if analysis['intervention_effectiveness']:
        eff = analysis['intervention_effectiveness']
        print(f"\nEffectiveness:")
        print(f"  Average ADS reduction: {eff.get('avg_reduction_with_intervention', 0):.4f}")
        print(f"  Scenarios benefiting: {eff.get('scenarios_benefiting', 0)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("report/assets/intervention_patterns.json"))
    args = parser.parse_args()
    
    analyze_interventions(args.run_id, args.output)

