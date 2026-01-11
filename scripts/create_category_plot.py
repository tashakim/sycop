#!/usr/bin/env python3
"""Create category breakdown plot."""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def create_category_plot(category_data_path: Path, output_path: Path):
    """Create bar chart of ADS by category."""
    with open(category_data_path) as f:
        data = json.load(f)
    
    categories = []
    baseline_means = []
    enforce_means = []
    baseline_errors = []
    enforce_errors = []
    
    for cat, cat_data in data.items():
        if 'baseline' in cat_data and 'enforce' in cat_data:
            baseline = cat_data['baseline'].get('ads', {})
            enforce = cat_data['enforce'].get('ads', {})
            
            if baseline and enforce:
                n_baseline = cat_data['baseline']['n']
                n_enforce = cat_data['enforce']['n']
                baseline_mean = baseline['mean']
                baseline_std = baseline.get('std', 0)
                enforce_mean = enforce['mean']
                enforce_std = enforce.get('std', 0)
                
                # Use Standard Error instead of Std Dev for error bars
                # SE = std / sqrt(n)
                baseline_se = baseline_std / np.sqrt(n_baseline) if n_baseline > 0 else 0
                enforce_se = enforce_std / np.sqrt(n_enforce) if n_enforce > 0 else 0
                
                categories.append(cat.replace('_', ' ').title())
                baseline_means.append(baseline_mean)
                enforce_means.append(enforce_mean)
                baseline_errors.append(baseline_se)
                enforce_errors.append(enforce_se)
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, baseline_means, width, label='Baseline', alpha=0.8, yerr=baseline_errors, capsize=3, error_kw={'elinewidth': 1.5})
    bars2 = ax.bar(x + width/2, enforce_means, width, label='Enforce', alpha=0.8, yerr=enforce_errors, capsize=3, error_kw={'elinewidth': 1.5})
    
    ax.set_xlabel('Category', fontsize=12)
    ax.set_ylabel('ADS (Agreement Drift Score)', fontsize=12)
    ax.set_title('ADS by Category: Baseline vs Enforcement', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Category plot saved to: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category-data", type=Path, default=Path("report/assets/category_breakdown.json"))
    parser.add_argument("--output", type=Path, default=Path("report/assets/fig_category_ads.png"))
    args = parser.parse_args()
    
    create_category_plot(args.category_data, args.output)

