"""Aggregate run-level tables into summaries with seed-clustered intervals."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

KEY_METRICS = [
    "contagion_radius", "peak_prevalence", "mean_first_passage", "t_saturation", "max_hops",
    "persisted", "persistence_rounds", "recovered", "recovery_time", "final_prevalence",
    "clean_acc_delta", "total_messages",
]


def bootstrap_ci(x: np.ndarray, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% percentile bootstrap CI of the mean, NaNs dropped. Deterministic."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return (np.nan, np.nan)
    if x.size == 1:
        return (float(x[0]), float(x[0]))
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n_boot, x.size), replace=True).mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def summarize(runs: pd.DataFrame, by: list[str], metrics: list[str] = KEY_METRICS) -> pd.DataFrame:
    """Summarise metrics while treating the random seed as the resampling unit.

    Several grid cells reuse a seed, so their stochastic draws are correlated. For
    marginal summaries (for example, one row per topology), first average within
    each seed and then bootstrap those seed-level means. A fully specified cell has
    one run per seed, so this reduces to the ordinary bootstrap across seeds.
    """
    rows = []
    for key, g in runs.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        row["n_runs"] = len(g)
        row["n_seeds"] = int(g["seed"].nunique())
        for m in metrics:
            v = g[m].astype(float)
            seed_means = (
                g.assign(_metric=v)
                .groupby("seed", sort=False)["_metric"]
                .mean()
                .dropna()
                .to_numpy()
            )
            lo, hi = bootstrap_ci(seed_means)
            row[m] = float(seed_means.mean()) if seed_means.size else np.nan
            row[f"{m}_lo"], row[f"{m}_hi"] = lo, hi
            row[f"{m}_n"] = int(v.notna().sum())
        rows.append(row)
    return pd.DataFrame(rows)


def spread_by_distance(agents: pd.DataFrame) -> pd.DataFrame:
    """Per topology and graph distance from the source: fraction of agents ever contaminated."""
    a = agents[~agents["is_source"] & agents["dist_from_source"].notna()].copy()
    a["infected"] = a["first_passage"].notna()
    g = a.groupby(["topology", "dist_from_source"]).agg(
        n_agents=("infected", "size"), frac_infected=("infected", "mean"),
        mean_first_passage=("first_passage", "mean"),
    )
    return g.reset_index()


def centrality_exposure(agents: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlation, per topology, between node measures and ever-contaminated (0/1) among reachable agents."""
    a = agents[~agents["is_source"] & agents["dist_from_source"].notna()].copy()
    a["infected"] = a["first_passage"].notna().astype(float)
    rows = []
    for topo, g in a.groupby("topology"):
        row = {"topology": topo, "n_agents": len(g)}
        for col in ("degree", "in_degree", "betweenness", "dist_from_source"):
            x = g[col].astype(float)
            # Spearman is Pearson correlation of ranks. Computing it directly keeps
            # SciPy out of the small core dependency set.
            row[f"spearman_{col}"] = (
                float(x.rank().corr(g["infected"].rank()))
                if x.nunique() > 1 and g["infected"].nunique() > 1
                else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def write_summaries(tables: dict[str, pd.DataFrame], out: Path, varied: list[str]) -> dict[str, pd.DataFrame]:
    runs = tables["runs"]
    res = {
        "summary_topology": summarize(runs, ["topology"]),
        "summary_cells": summarize(runs, list(dict.fromkeys(["topology"] + varied))),
        "spread_by_distance": spread_by_distance(tables["agents"]),
        "centrality_exposure": centrality_exposure(tables["agents"]),
    }
    for name, df in res.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return res
