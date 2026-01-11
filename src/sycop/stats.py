"""Statistical analysis: bootstrap CIs and permutation tests."""

import numpy as np
from typing import Optional
from scipy import stats


def bootstrap_ci(
    values: list[float],
    n_resamples: int = 2000,
    alpha: float = 0.05,
    random_seed: Optional[int] = None,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval.
    
    Args:
        values: List of metric values (one per scenario)
        n_resamples: Number of bootstrap resamples
        alpha: Significance level (e.g., 0.05 for 95% CI)
        random_seed: Random seed for reproducibility
    
    Returns:
        (mean, ci_low, ci_high)
    """
    if not values:
        return 0.0, 0.0, 0.0
    
    values = np.array(values)
    mean = np.mean(values)
    
    if random_seed is not None:
        np.random.seed(random_seed)
    
    # Bootstrap resampling
    n = len(values)
    resampled_means = []
    for _ in range(n_resamples):
        sample = np.random.choice(values, size=n, replace=True)
        resampled_means.append(np.mean(sample))
    
    resampled_means = np.array(resampled_means)
    
    # Percentile method
    ci_low = np.percentile(resampled_means, 100 * alpha / 2)
    ci_high = np.percentile(resampled_means, 100 * (1 - alpha / 2))
    
    return float(mean), float(ci_low), float(ci_high)


def paired_permutation_test(
    baseline_values: list[float],
    treatment_values: list[float],
    n_permutations: int = 5000,
    random_seed: Optional[int] = None,
) -> dict:
    """
    Paired permutation test for baseline vs treatment.
    
    Args:
        baseline_values: Metric values for baseline condition
        treatment_values: Metric values for treatment condition
        n_permutations: Number of permutation trials
        random_seed: Random seed for reproducibility
    
    Returns:
        Dictionary with test statistics
    """
    if len(baseline_values) != len(treatment_values):
        raise ValueError("baseline and treatment must have same length")
    
    if random_seed is not None:
        np.random.seed(random_seed)
    
    # Compute observed difference
    diffs = np.array(treatment_values) - np.array(baseline_values)
    observed_mean_diff = np.mean(diffs)
    
    # Permutation test
    n = len(diffs)
    permuted_means = []
    for _ in range(n_permutations):
        # Randomly flip signs
        signs = np.random.choice([-1, 1], size=n)
        permuted_diffs = diffs * signs
        permuted_means.append(np.mean(permuted_diffs))
    
    permuted_means = np.array(permuted_means)
    
    # p-value: fraction of permuted |mean| >= observed |mean|
    p_value = np.mean(np.abs(permuted_means) >= np.abs(observed_mean_diff))
    
    return {
        "mean_diff": float(observed_mean_diff),
        "p_value": float(p_value),
        "significant": p_value < 0.05,
    }


def aggregate_metrics(
    scenario_metrics: list[dict],
    condition: str,
    bootstrap_resamples: int = 2000,
    ci_alpha: float = 0.05,
    random_seed: Optional[int] = None,
) -> dict:
    """
    Aggregate metrics across scenarios with CIs.
    
    Args:
        scenario_metrics: List of metric dicts (one per scenario)
        condition: Condition name
        bootstrap_resamples: Number of bootstrap resamples
        ci_alpha: Significance level
        random_seed: Random seed
    
    Returns:
        Dictionary of aggregated metrics with CIs
    """
    # Extract metric values (filter None for conditional metrics)
    ads_values = [m["ads"] for m in scenario_metrics if m.get("ads") is not None]
    csd_values = [m["csd"] for m in scenario_metrics if m.get("csd") is not None]
    nsi_values = [m["nsi"] for m in scenario_metrics if m.get("nsi") is not None]
    refusal_values = [m["refusal_rate"] for m in scenario_metrics]
    task_success_values = [m["task_success"] for m in scenario_metrics]
    
    aggregates = {
        "condition": condition,
        "n_scenarios": len(scenario_metrics),
    }
    
    # Compute CIs for each metric
    if ads_values:
        aggregates["ads"] = bootstrap_ci(ads_values, bootstrap_resamples, ci_alpha, random_seed)
    if csd_values:
        aggregates["csd"] = bootstrap_ci(csd_values, bootstrap_resamples, ci_alpha, random_seed)
    if nsi_values:
        aggregates["nsi"] = bootstrap_ci(nsi_values, bootstrap_resamples, ci_alpha, random_seed)
    
    aggregates["refusal_rate"] = bootstrap_ci(refusal_values, bootstrap_resamples, ci_alpha, random_seed)
    aggregates["task_success"] = bootstrap_ci(task_success_values, bootstrap_resamples, ci_alpha, random_seed)
    
    return aggregates

