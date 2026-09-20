"""Run an experiment specification: every grid cell x every seed, each with a paired no-fault control."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from .config import ExperimentSpec, load_spec
from .metrics import compute_metrics
from .simulation import RunResult, simulate


def run_experiment(spec: ExperimentSpec, progress: bool = False) -> dict[str, pd.DataFrame]:
    runs, series, agents = [], [], []
    control_cache: dict[tuple, RunResult] = {}
    cfgs = spec.configs()
    for ci, cfg in enumerate(cfgs):
        for seed in spec.seeds:
            run_id = f"{spec.name}-c{ci:04d}-s{seed}"
            res = simulate(cfg, seed, fault=True)
            # the control does not depend on where the fault would have been injected
            ckey = (tuple(sorted(replace(cfg, fault_location="central").to_dict().items())), seed)
            if ckey not in control_cache:
                control_cache[ckey] = simulate(cfg, seed, fault=False)
            ctrl = control_cache[ckey]
            m = compute_metrics(res, ctrl)
            runs.append({"run_id": run_id, "cell": ci, "seed": seed, **cfg.to_dict(), "source": res.source,
                         "source_role": res.roles[res.source], **res.net, **m})
            for r, rc in zip(res.series, ctrl.series):
                series.append({"run_id": run_id, "cell": ci, "seed": seed, "topology": cfg.topology,
                               **r, "clean_acc_control": rc["clean_acc"]})
            for v, st in res.node_stats.items():
                fpt = res.first_infected.get(v)
                agents.append({"run_id": run_id, "cell": ci, "seed": seed, "topology": cfg.topology, "agent": v,
                               "role": res.roles[v], "is_source": v == res.source, **st,
                               "first_passage": float(fpt) if fpt is not None else float("nan")})
        if progress:
            print(f"  cell {ci + 1}/{len(cfgs)} done", flush=True)
    return {"runs": pd.DataFrame(runs), "timeseries": pd.DataFrame(series), "agents": pd.DataFrame(agents)}


def run_from_file(path: str | Path, out: str | Path, figures: bool = True, progress: bool = False) -> dict[str, pd.DataFrame]:
    from .analysis import write_summaries  # local import keeps `experiment` light
    spec = load_spec(path)
    tables = run_experiment(spec, progress=progress)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    tables.update(write_summaries(tables, out, spec.varied))
    if figures:
        from .viz import make_all_figures
        make_all_figures(tables, spec, out)
    return tables
