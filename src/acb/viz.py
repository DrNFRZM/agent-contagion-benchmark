"""Plain matplotlib figures: network diagrams, contagion curves, topology comparisons.

Colour is used for identity (topology, fixed order) and, in the network diagrams,
one sequential ramp for first-passage time. Text stays in neutral ink.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .config import ExperimentSpec, RunConfig  # noqa: E402
from .simulation import simulate  # noqa: E402

INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#dcdad4", "#fcfcfb"
TOPO_STYLE = {  # fixed identity: colour + marker + linestyle (never colour alone)
    "star": ("#2a78d6", "o", "-"),
    "pipeline": ("#eb6834", "s", "--"),
    "dag": ("#1baf7a", "^", "-."),
    "graph": ("#eda100", "D", ":"),
}
RAMP = LinearSegmentedColormap.from_list("fpt", ["#b7d3f6", "#3987e5", "#0d366b"])
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
    "axes.titleweight": "regular", "legend.frameon": False,
})


def _layout(G: nx.DiGraph, topo: str) -> dict:
    n = G.number_of_nodes()
    if topo == "star":
        return nx.shell_layout(G, nlist=[[0], list(range(1, n))])
    if topo == "pipeline":
        return {i: (i / max(n - 1, 1) * 2 - 1, 0.0) for i in range(n)}
    if topo == "dag":
        pos = {}
        for x, layer in enumerate(nx.topological_generations(G)):
            for j, v in enumerate(sorted(layer)):
                pos[v] = (x, (j - (len(layer) - 1) / 2) * 0.9)
        return pos
    return nx.circular_layout(G)


def _topo_order(present) -> list[str]:
    return [t for t in TOPO_STYLE if t in set(present)]


def fig_networks(runs: pd.DataFrame, out: Path) -> Path:
    topos = _topo_order(runs["topology"])
    fig, axes = plt.subplots(1, len(topos), figsize=(3.6 * len(topos), 3.6), squeeze=False)
    for ax, topo in zip(axes[0], topos):
        row = runs[runs["topology"] == topo].sort_values(["cell", "seed"]).iloc[0]
        cfg = RunConfig.from_row(row)
        res = simulate(cfg, int(row["seed"]), fault=True)
        G = nx.DiGraph(res.edges)
        G.add_nodes_from(range(cfg.n_agents))
        pos = _layout(G, topo)
        hit = res.first_infected
        tmax = max([t for t in hit.values()] + [1])
        colors = [RAMP(hit[v] / tmax) if v in hit else "#e6e4de" for v in G.nodes]
        ax.set_axis_off()
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#b9b7b0", width=0.9, arrows=True, arrowsize=8,
                               node_size=380, connectionstyle="arc3,rad=0.08")
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, node_size=380, edgecolors="#8a8880", linewidths=0.8)
        nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=[res.source], node_color="none", node_size=520,
                               edgecolors=INK, linewidths=2.0)
        labels = {v: str(v) for v in G.nodes}
        nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=7, font_color=INK)
        reached = len(hit) - 1
        ax.set_title(f"{topo}  (source ringed; reached {reached}/{cfg.n_agents - 1})\n"
                     f"seed {int(row['seed'])}, {cfg.retention}, fault at {cfg.fault_location}", fontsize=8.5)
    fig.text(0.5, 0.01, "node shade = round of first contamination (light early, dark late); grey = never contaminated",
             ha="center", color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    p = out / "fig_networks.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def fig_curves(runs: pd.DataFrame, ts: pd.DataFrame, spec: ExperimentSpec, out: Path) -> Path:
    facet = "retention" if "retention" in spec.varied else None
    levels = sorted(runs[facet].unique(), key=str) if facet else [None]
    fig, axes = plt.subplots(1, len(levels), figsize=(4.4 * len(levels), 3.5), sharey=True, squeeze=False)
    R = runs["repair_round"].dropna().unique()
    df = ts.merge(runs[["run_id", *( [facet] if facet else [] )]], on="run_id")
    for ax, lv in zip(axes[0], levels):
        d = df if lv is None else df[df[facet] == lv]
        for topo in _topo_order(d["topology"]):
            col, mk, ls = TOPO_STYLE[topo]
            piv = d[d["topology"] == topo].pivot_table(index="t", columns="run_id", values="prevalence")
            m, lo, hi = piv.mean(axis=1), piv.quantile(0.25, axis=1), piv.quantile(0.75, axis=1)
            ax.fill_between(m.index, lo, hi, color=col, alpha=0.12, linewidth=0)
            ax.plot(m.index, m.values, color=col, ls=ls, lw=2, marker=mk, markersize=3.5, markevery=3, label=topo)
        if len(R) == 1:
            ax.axvline(float(R[0]), color=INK2, lw=0.9, ls=(0, (2, 3)))
            ax.text(float(R[0]) + 0.3, ax.get_ylim()[1] * 0.97, "source repaired", color=INK2, fontsize=7.5, va="top")
        ax.set_title(f"retention: {lv}" if lv else "all runs")
        ax.set_xlabel("round")
    axes[0][0].set_ylabel("contaminated fraction of agents")
    axes[0][0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Contagion over time (mean over runs; band = interquartile range)", fontsize=10, color=INK)
    fig.tight_layout()
    p = out / "fig_curves.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def _errbar(ax, x, mean, lo, hi, col, mk):
    ax.errorbar(x, mean, yerr=[[max(mean - lo, 0)], [max(hi - mean, 0)]], color=col, marker=mk, markersize=6,
                capsize=3, lw=1.4, ls="none", markeredgecolor=SURFACE, markeredgewidth=1.2)


def fig_topology_comparison(summary: pd.DataFrame, out: Path) -> Path:
    panels = [("contagion_radius", "contagion radius\n(fraction of other agents ever contaminated)"),
              ("mean_first_passage", "mean first-passage time\n(rounds, reached agents only)"),
              ("persisted", "persistence\n(fraction of runs still contaminated at horizon)"),
              ("recovery_time", "recovery time after repair\n(rounds, runs that recovered only)")]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
    topos = _topo_order(summary["topology"])
    for ax, (m, title) in zip(axes, panels):
        for i, topo in enumerate(topos):
            r = summary[summary["topology"] == topo].iloc[0]
            col, mk, _ = TOPO_STYLE[topo]
            if not np.isnan(r[m]):
                _errbar(ax, i, r[m], r[f"{m}_lo"], r[f"{m}_hi"], col, mk)
        ax.set_xticks(range(len(topos)), topos)
        ax.set_xlim(-0.6, len(topos) - 0.4)
        ax.set_title(title, fontsize=8.5)
        if m in ("contagion_radius", "persisted"):
            ax.set_ylim(0, 1)
        else:
            ax.set_ylim(bottom=0)
    fig.suptitle("Topology comparison (mean and 95% seed-clustered bootstrap interval)", fontsize=10, color=INK)
    fig.tight_layout()
    p = out / "fig_topology_comparison.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def fig_factor_breakdown(cells: pd.DataFrame, varied: list[str], out: Path) -> Path | None:
    others = [v for v in varied if v != "topology"]
    if not others:
        return None
    factor = others[0]
    levels = sorted(cells[factor].unique(), key=str)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    topos = _topo_order(cells["topology"])
    w = 0.8 / len(levels)
    shades = [0.35, 0.65, 1.0, 0.5]
    for ax, (m, title) in zip(axes, [("contagion_radius", "contagion radius"), ("persisted", "persisted at horizon")]):
        for j, lv in enumerate(levels):
            for i, topo in enumerate(topos):
                d = cells[(cells["topology"] == topo) & (cells[factor] == lv)]
                if d.empty:
                    continue
                w_ = d["n_runs"].to_numpy()
                mean = float(np.average(d[m], weights=w_))
                ax.bar(i + (j - (len(levels) - 1) / 2) * w, mean, width=w * 0.92, color=TOPO_STYLE[topo][0],
                       alpha=shades[j % len(shades)], label=str(lv) if i == 0 else None,
                       hatch=["", "//", "..", "xx"][j % 4], edgecolor=SURFACE, linewidth=0.6)
        ax.set_xticks(range(len(topos)), topos)
        ax.set_ylim(0, 1)
        ax.set_title(title)
    axes[0].legend(title=factor, fontsize=8, loc="upper left")
    fig.suptitle(f"Effect of {factor} within each topology (hatch = level; mean over other factors and seeds)", fontsize=10, color=INK)
    fig.tight_layout()
    p = out / f"fig_breakdown_{factor}.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def fig_spread_by_distance(sbd: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for topo in _topo_order(sbd["topology"]):
        d = sbd[sbd["topology"] == topo].sort_values("dist_from_source")
        col, mk, ls = TOPO_STYLE[topo]
        ax.plot(d["dist_from_source"], d["frac_infected"], color=col, ls=ls, marker=mk, lw=2, markersize=4, label=topo)
    ax.set_xlabel("graph distance from source (hops)")
    ax.set_ylabel("fraction of agents ever contaminated")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8)
    ax.set_title("Spread by distance from the source")
    fig.tight_layout()
    p = out / "fig_spread_by_distance.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def make_all_figures(tables: dict[str, pd.DataFrame], spec: ExperimentSpec, out: Path) -> list[Path]:
    paths = [
        fig_networks(tables["runs"], out),
        fig_curves(tables["runs"], tables["timeseries"], spec, out),
        fig_topology_comparison(tables["summary_topology"], out),
        fig_spread_by_distance(tables["spread_by_distance"], out),
    ]
    extra = fig_factor_breakdown(tables["summary_cells"], spec.varied, out)
    if extra:
        paths.append(extra)
    return paths
