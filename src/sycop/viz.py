"""Visualization: generate plots for reports."""

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np


def plot_turn_drift(
    turn_data: dict[str, list[float]],
    output_path: Path,
    title: str = "Agreement Drift Over Turns",
) -> None:
    """
    Plot agreement probability vs turn index for different conditions.
    
    Args:
        turn_data: Dict mapping condition -> list of agreement probabilities per turn
        output_path: Where to save the plot
        title: Plot title
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for condition, values in turn_data.items():
        ax.plot(range(len(values)), values, marker="o", label=condition, linewidth=2)
    
    ax.set_xlabel("Turn Index", fontsize=12)
    ax.set_ylabel("Agreement Probability", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-0.05, 1.05)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_nsi_over_turns(
    turn_data: dict[str, list[float]],
    output_path: Path,
    title: str = "Normative Softening Index Over Turns",
) -> None:
    """Plot NSI vs turn index."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for condition, values in turn_data.items():
        ax.plot(range(len(values)), values, marker="o", label=condition, linewidth=2)
    
    ax.set_xlabel("Turn Index", fontsize=12)
    ax.set_ylabel("NSI (Rapport / (Rapport + Epistemic))", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-0.05, 1.05)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_category_breakdown(
    category_data: dict[str, dict[str, tuple[float, float, float]]],
    metric_name: str,
    output_path: Path,
    title: Optional[str] = None,
) -> None:
    """
    Plot bar chart of metric by category.
    
    Args:
        category_data: Dict mapping category -> condition -> (mean, ci_low, ci_high)
        metric_name: Name of metric (e.g., "ADS")
        output_path: Where to save the plot
        title: Plot title (auto-generated if None)
    """
    if title is None:
        title = f"{metric_name} by Category"
    
    categories = list(category_data.keys())
    conditions = list(next(iter(category_data.values())).keys())
    
    x = np.arange(len(categories))
    width = 0.8 / len(conditions)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for i, condition in enumerate(conditions):
        means = [category_data[cat][condition][0] for cat in categories]
        ci_lows = [category_data[cat][condition][1] for cat in categories]
        ci_highs = [category_data[cat][condition][2] for cat in categories]
        
        offset = (i - len(conditions) / 2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=condition, alpha=0.8)
        
        # Add error bars (CI)
        ax.errorbar(
            x + offset,
            means,
            yerr=[[m - l for m, l in zip(means, ci_lows)],
                  [h - m for h, m in zip(ci_highs, means)]],
            fmt="none",
            color="black",
            capsize=3,
        )
    
    ax.set_xlabel("Category", fontsize=12)
    ax.set_ylabel(metric_name, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

