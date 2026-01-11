"""CLI interface using Typer."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from sycop.config import RunConfig
from sycop.config import Settings
from sycop.suite import Suite
from sycop.runner import Runner
from sycop.labeling import Labeler
from sycop.metrics import compute_scenario_metrics, compute_intervention_rate
from sycop.stats import aggregate_metrics, paired_permutation_test
from sycop.storage import read_transcripts, read_labels, load_config
from sycop.viz import plot_turn_drift, plot_nsi_over_turns, plot_category_breakdown
from sycop.artifacts import generate_table1, generate_report_markdown

app = typer.Typer(help="Sycophancy Under Pressure: trajectory-level evaluation")
console = Console()


@app.command()
def run(
    config_path: Path = typer.Option(..., "--config", "-c", help="Path to config YAML"),
    base_path: Path = typer.Option(Path("runs"), "--base-path", help="Base path for runs"),
):
    """Run scenarios and generate transcripts."""
    console.print(f"[bold]Loading config from {config_path}[/bold]")
    config = RunConfig.from_yaml(Path(config_path).resolve())
    
    console.print(f"[bold]Loading suite from {config.suite.path}[/bold]")
    suite = Suite.from_yaml(Path(config.suite.path).resolve())
    
    if config.suite.max_scenarios:
        suite = suite.limit(config.suite.max_scenarios)
    
    console.print(f"[bold]Running {len(suite.scenarios)} scenarios under {len(config.conditions)} conditions[/bold]")
    
    runner = Runner(config)
    run_path = runner.run(suite, base_path)
    
    console.print(f"[green]✓ Run complete. Output: {run_path}[/green]")
    console.print(f"[bold]Run ID: {run_path.name}[/bold]")
    return run_path.name  # Return run_id for chaining


@app.command()
def label(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to label"),
    method: str = typer.Option("hybrid", "--method", help="Labeling method (heuristic/hybrid)"),
    base_path: Path = typer.Option(Path("runs"), "--base-path", help="Base path for runs"),
):
    """Label transcripts."""
    run_path = base_path / run_id
    if not run_path.exists():
        console.print(f"[red]Error: Run {run_id} not found[/red]")
        raise typer.Exit(1)
    
    config_dict = load_config(run_path)
    config = RunConfig(**config_dict)
    
    console.print(f"[bold]Loading transcripts from {run_path}[/bold]")
    transcripts = read_transcripts(run_path)
    
    if not transcripts:
        console.print("[red]Error: No transcripts found[/red]")
        raise typer.Exit(1)
    
    # Initialize labeler
    if method == "hybrid":
        labeler = Labeler(
            gate_model_config=config.models.get("gate"),
            correction_strength_model_config=config.models.get("gate"),  # Reuse gate model
            settings=Settings(),
        )
    else:
        labeler = Labeler()
    
    console.print(f"[bold]Labeling {len(transcripts)} turns...[/bold]")
    
    from sycop.storage import write_labels_jsonl
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Labeling...", total=len(transcripts))
        
        for transcript in transcripts:
            premise = transcript["meta"]["contested_premise"]
            reply = transcript["assistant"]
            
            labels = labeler.label_turn(premise, reply, method)
            
            label_record = {
                "run_id": transcript["run_id"],
                "condition": transcript["condition"],
                "scenario_id": transcript["scenario_id"],
                "turn_idx": transcript["turn_idx"],
                "assistant": reply,
                **labels,
            }
            
            write_labels_jsonl(run_path, label_record)
            progress.update(task, advance=1)
    
    console.print(f"[green]✓ Labeling complete[/green]")


@app.command()
def score(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to score"),
    base_path: Path = typer.Option(Path("runs"), "--base-path", help="Base path for runs"),
):
    """Compute metrics and statistics."""
    run_path = base_path / run_id
    if not run_path.exists():
        console.print(f"[red]Error: Run {run_id} not found[/red]")
        raise typer.Exit(1)
    
    config_dict = load_config(run_path)
    config = RunConfig(**config_dict)
    
    console.print(f"[bold]Loading transcripts and labels...[/bold]")
    transcripts = read_transcripts(run_path)
    labels = read_labels(run_path)
    
    if not transcripts or not labels:
        console.print("[red]Error: Missing transcripts or labels[/red]")
        raise typer.Exit(1)
    
    # Index labels by (scenario_id, condition, turn_idx)
    label_index = {}
    for label in labels:
        key = (label["scenario_id"], label["condition"], label["turn_idx"])
        label_index[key] = label
    
    # Group by scenario and condition
    scenario_turns = {}
    for transcript in transcripts:
        key = (transcript["scenario_id"], transcript["condition"])
        if key not in scenario_turns:
            scenario_turns[key] = []
        
        turn_key = (transcript["scenario_id"], transcript["condition"], transcript["turn_idx"])
        label = label_index.get(turn_key, {})
        
        scenario_turns[key].append({
            **transcript,
            **label,
        })
    
    # Compute metrics per scenario
    console.print("[bold]Computing metrics...[/bold]")
    scenario_metrics = {}
    for (scenario_id, condition), turns in scenario_turns.items():
        correction_required = turns[0]["meta"]["correction_required"]
        metrics = compute_scenario_metrics(turns, correction_required)
        
        # Add intervention rate for enforce condition
        if condition == "enforce":
            rewritten_flags = []
            for turn in turns:
                enforcement = turn.get("meta", {}).get("enforcement", {})
                rewritten = enforcement.get("rewritten", False)
                rewritten_flags.append(rewritten)
            metrics["intervention_rate"] = compute_intervention_rate(rewritten_flags)
        
        scenario_metrics[(scenario_id, condition)] = metrics
    
    # Save per-scenario metrics (convert tuple keys to strings, numpy types to native)
    import numpy as np
    
    def convert_to_native(obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_native(item) for item in obj]
        elif obj is None:
            return None
        else:
            return obj
    
    metrics_path = run_path / "metrics.json"
    metrics_serializable = {
        f"{scenario_id}_{condition}": convert_to_native(metrics)
        for (scenario_id, condition), metrics in scenario_metrics.items()
    }
    with open(metrics_path, "w") as f:
        json.dump(metrics_serializable, f, indent=2)
    
    # Aggregate by condition
    console.print("[bold]Computing aggregates...[/bold]")
    condition_metrics = {}
    for condition in config.conditions:
        cond_scenario_metrics = [
            m for (sid, c), m in scenario_metrics.items()
            if c == condition
        ]
        
        aggregates = aggregate_metrics(
            cond_scenario_metrics,
            condition,
            config.stats.bootstrap_resamples,
            config.stats.ci_alpha,
            config.seed,
        )
        
        # Add intervention rate for enforce condition
        if condition == "enforce":
            intervention_rates = [
                m.get("intervention_rate", 0) for m in cond_scenario_metrics
                if "intervention_rate" in m
            ]
            if intervention_rates:
                from sycop.stats import bootstrap_ci
                aggregates["intervention_rate"] = bootstrap_ci(
                    intervention_rates,
                    config.stats.bootstrap_resamples,
                    config.stats.ci_alpha,
                    config.seed,
                )
        
        condition_metrics[condition] = aggregates
    
    # Paired permutation test (baseline vs enforce)
    if "baseline" in condition_metrics and "enforce" in condition_metrics:
        console.print("[bold]Running permutation test...[/bold]")
        baseline_ads = [
            m["ads"] for (sid, c), m in scenario_metrics.items()
            if c == "baseline" and m.get("ads") is not None
        ]
        enforce_ads = [
            m["ads"] for (sid, c), m in scenario_metrics.items()
            if c == "enforce" and m.get("ads") is not None
        ]
        
        if len(baseline_ads) == len(enforce_ads) and baseline_ads:
            test_result = paired_permutation_test(
                baseline_ads,
                enforce_ads,
                config.stats.permutation_trials,
                config.seed,
            )
            condition_metrics["baseline_vs_enforce"] = test_result
    
    # Save aggregates (convert numpy types)
    aggregates_path = run_path / "aggregates.json"
    aggregates_serializable = convert_to_native(condition_metrics)
    with open(aggregates_path, "w") as f:
        json.dump(aggregates_serializable, f, indent=2)
    
    console.print(f"[green]✓ Scoring complete. Results: {aggregates_path}[/green]")


@app.command()
def report(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to report"),
    output_dir: Path = typer.Option(Path("report/assets"), "--out", help="Output directory"),
    base_path: Path = typer.Option(Path("runs"), "--base-path", help="Base path for runs"),
):
    """Generate report artifacts (tables and plots)."""
    run_path = base_path / run_id
    if not run_path.exists():
        console.print(f"[red]Error: Run {run_id} not found[/red]")
        raise typer.Exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[bold]Loading aggregates...[/bold]")
    aggregates_path = run_path / "aggregates.json"
    if not aggregates_path.exists():
        console.print("[red]Error: aggregates.json not found. Run 'sycop score' first.[/red]")
        raise typer.Exit(1)
    
    with open(aggregates_path, "r") as f:
        aggregates = json.load(f)
    
    # Filter to condition aggregates only
    condition_aggregates = {
        k: v for k, v in aggregates.items()
        if k != "baseline_vs_enforce"
    }
    
    # Generate Table 1
    console.print("[bold]Generating Table 1...[/bold]")
    table1_path = output_dir / "table1.md"
    generate_table1(condition_aggregates, table1_path)
    
    # Generate plots - aggregate turn-level data
    console.print("[bold]Generating plots...[/bold]")
    
    # Load transcripts and labels for turn-level aggregation
    transcripts = read_transcripts(run_path)
    labels = read_labels(run_path)
    
    # Index labels
    label_index = {}
    for label in labels:
        key = (label["scenario_id"], label["condition"], label["turn_idx"])
        label_index[key] = label
    
    # Aggregate turn-level data by condition
    max_turns = max((t["turn_idx"] for t in transcripts), default=0) + 1
    
    # Agreement drift plot
    agreement_by_turn = {cond: [] for cond in condition_aggregates.keys()}
    nsi_by_turn = {cond: [] for cond in condition_aggregates.keys()}
    
    for turn_idx in range(max_turns):
        for condition in condition_aggregates.keys():
            # Aggregate agreement probability at this turn
            agreements = []
            nsi_values = []
            
            for transcript in transcripts:
                if transcript["condition"] == condition and transcript["turn_idx"] == turn_idx:
                    key = (transcript["scenario_id"], condition, turn_idx)
                    label = label_index.get(key, {})
                    
                    # Agreement
                    agreement = label.get("agreement", {})
                    if isinstance(agreement, dict) and agreement.get("endorses_premise") is not None:
                        agreements.append(1 if agreement["endorses_premise"] else 0)
                    
                    # NSI
                    rapport = label.get("rapport_count", 0)
                    epistemic = label.get("epistemic_count", 0)
                    if rapport + epistemic > 0:
                        nsi_values.append(rapport / (rapport + epistemic))
            
            agreement_by_turn[condition].append(
                sum(agreements) / len(agreements) if agreements else 0.0
            )
            nsi_by_turn[condition].append(
                sum(nsi_values) / len(nsi_values) if nsi_values else 0.0
            )
    
    # Generate plots
    if any(len(v) > 0 for v in agreement_by_turn.values()):
        plot_turn_drift(agreement_by_turn, output_dir / "fig_turn_drift.png")
        console.print("  ✓ Generated fig_turn_drift.png")
    
    if any(len(v) > 0 for v in nsi_by_turn.values()):
        plot_nsi_over_turns(nsi_by_turn, output_dir / "fig_nsi.png")
        console.print("  ✓ Generated fig_nsi.png")
    
    # Category breakdown plot (if we have category data)
    config_dict = load_config(run_path)
    config = RunConfig(**config_dict)
    
    # Aggregate by category
    category_metrics = {}
    for transcript in transcripts:
        category = transcript.get("category")
        condition = transcript["condition"]
        if category and condition in condition_aggregates:
            if category not in category_metrics:
                category_metrics[category] = {c: [] for c in condition_aggregates.keys()}
            
            key = (transcript["scenario_id"], condition, transcript["turn_idx"])
            label = label_index.get(key, {})
            # This is simplified - would need scenario-level aggregation
            # For now, skip category breakdown or implement properly
    
    # Generate report markdown
    report_path = output_dir / "report.md"
    generate_report_markdown(run_id, condition_aggregates, report_path)
    
    console.print(f"[green]✓ Report generated: {output_dir}[/green]")


@app.command()
def all(
    config_path: Path = typer.Option(..., "--config", "-c", help="Path to config YAML"),
    base_path: Path = typer.Option(Path("runs"), "--base-path", help="Base path for runs"),
    output_dir: Path = typer.Option(Path("report/assets"), "--out", help="Output directory"),
    method: str = typer.Option("hybrid", "--method", help="Labeling method (heuristic/hybrid)"),
):
    """Run full pipeline: run -> label -> score -> report."""
    console.print("[bold]Running full pipeline...[/bold]")
    
    # Step 1: Run
    console.print("\n[bold cyan]Step 1/4: Running scenarios...[/bold cyan]")
    config = RunConfig.from_yaml(Path(config_path).resolve())
    suite = Suite.from_yaml(Path(config.suite.path).resolve())
    if config.suite.max_scenarios:
        suite = suite.limit(config.suite.max_scenarios)
    
    runner = Runner(config)
    run_path = runner.run(suite, base_path)
    run_id = run_path.name
    
    console.print(f"[green]✓ Run complete. Run ID: {run_id}[/green]")
    
    # Step 2: Label
    console.print(f"\n[bold cyan]Step 2/4: Labeling transcripts...[/bold cyan]")
    label(run_id=run_id, method=method, base_path=base_path)
    
    # Step 3: Score
    console.print(f"\n[bold cyan]Step 3/4: Computing metrics...[/bold cyan]")
    score(run_id=run_id, base_path=base_path)
    
    # Step 4: Report
    console.print(f"\n[bold cyan]Step 4/4: Generating report...[/bold cyan]")
    report(run_id=run_id, output_dir=output_dir, base_path=base_path)
    
    console.print(f"\n[bold green]✓ Full pipeline complete![/bold green]")
    console.print(f"Results: {run_path}")
    console.print(f"Report: {output_dir}")

