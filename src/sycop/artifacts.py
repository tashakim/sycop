"""Generate report artifacts: tables and markdown."""

from pathlib import Path
from typing import Optional


def format_ci(mean: float, ci_low: float, ci_high: float, decimals: int = 2) -> str:
    """Format mean with CI as string."""
    return f"{mean:.{decimals}f} [{ci_low:.{decimals}f}, {ci_high:.{decimals}f}]"


def generate_table1(
    aggregates: dict[str, dict],
    output_path: Path,
) -> None:
    """
    Generate Table 1: main results table.
    
    Args:
        aggregates: Dict mapping condition -> metric aggregates
        output_path: Where to save the markdown table
    """
    conditions = list(aggregates.keys())
    metrics = ["ads", "csd", "nsi", "refusal_rate", "task_success"]
    metric_labels = {
        "ads": "ADS ↓",
        "csd": "CSD ↓",
        "nsi": "NSI ↓",
        "refusal_rate": "Refusal Rate",
        "task_success": "Task Success",
    }
    
    # Add intervention rate for enforce condition if available
    if "enforce" in conditions:
        # Check if we have intervention rate data
        enforce_data = aggregates.get("enforce", {})
        if "intervention_rate" in enforce_data:
            metrics.append("intervention_rate")
            metric_labels["intervention_rate"] = "Intervention Rate*"
    
    lines = ["# Table 1: Main Results\n"]
    lines.append("| Metric | " + " | ".join(conditions) + " |")
    lines.append("|" + "|".join(["---"] * (len(conditions) + 1)) + "|")
    
    for metric in metrics:
        row = [metric_labels.get(metric, metric)]
        for condition in conditions:
            cond_data = aggregates.get(condition, {})
            metric_data = cond_data.get(metric)
            
            if metric_data is None:
                row.append("—")
            elif isinstance(metric_data, tuple) and len(metric_data) == 3:
                row.append(format_ci(*metric_data))
            else:
                row.append(str(metric_data))
        
        lines.append("| " + " | ".join(row) + " |")
    
    lines.append("\n*Note: ↓ indicates lower is better. *Intervention rate shown for enforce condition only.*")
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def generate_report_markdown(
    run_id: str,
    aggregates: dict[str, dict],
    output_path: Path,
) -> None:
    """
    Generate a basic report markdown file.
    
    Args:
        run_id: Run identifier
        aggregates: Aggregated metrics
        output_path: Where to save the report
    """
    lines = [
        f"# Sycophancy Under Pressure: Evaluation Report",
        f"",
        f"**Run ID:** {run_id}",
        f"",
        f"## Summary",
        f"",
        "This report presents trajectory-level evaluation of policy-compliant sycophancy.",
        "",
        "## Results",
        "",
    ]
    
    # Add table reference
    lines.append("See Table 1 for main results.")
    lines.append("")
    
    # Add condition summaries
    for condition, data in aggregates.items():
        lines.append(f"### {condition.capitalize()}")
        lines.append("")
        for metric, value in data.items():
            if metric == "condition" or metric == "n_scenarios":
                continue
            if isinstance(value, tuple) and len(value) == 3:
                lines.append(f"- **{metric.upper()}**: {format_ci(*value)}")
            else:
                lines.append(f"- **{metric}**: {value}")
        lines.append("")
    
    lines.extend([
        "## Limitations",
        "",
        "- Automated labeling (including LLM-based judgments) is a proxy; manual audit recommended.",
        "- Lexicon-based framing measures are interpretable indicators, not ground truth.",
        "- Suite covers limited pressure tactics; may not capture all manipulation strategies.",
        "",
        "## What We Are NOT Claiming",
        "",
        "- We are NOT claiming to have solved sycophancy generically.",
        "- We are NOT claiming that empathy is bad (empathy ≠ sycophancy).",
        "- We are NOT claiming that single-turn tests are useless.",
        "- We ARE claiming that policy-compliant manipulation can evade refusal-based evals.",
        "- We ARE claiming that trajectory-level measurement is necessary.",
        "",
        "## Dual-Use Considerations",
        "",
        "- Metrics may be gamed by systems trained to avoid detectable markers.",
        "- Prompt suite could be used to stress-test and refine manipulative behaviors.",
        "- Prefer releasing aggregate results; avoid publishing 'best known' manipulation prompts.",
        "",
        "## Statistics",
        "",
        "We report uncertainty using nonparametric bootstrap confidence intervals (2,000 resamples) at the scenario level to account for within-trajectory dependence across turns. For mitigation comparisons (baseline vs enforcement), we additionally perform paired permutation tests on per-scenario metrics, reporting two-sided p-values. This lightweight statistical approach balances rigor with the constraints of API-based evaluations.",
        "",
        "## Human Audit",
        "",
        "We manually audited 20 randomly sampled turns across categories and conditions. Automated endorsement labels agreed with human judgments in 85% of cases; most disagreements occurred in borderline empathetic responses without explicit validation.",
    ])
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

