"""Per-run metrics computed from a RunResult (see docs/research_note.md for definitions).

Notation: N agents, source s, n_t = number of contaminated agents at the end of round t
(t = 0 is the state right after injection), f_t = n_t / N (prevalence), R = repair round.
"""
from __future__ import annotations

import math

import numpy as np

from .simulation import RunResult

NAN = math.nan


def compute_metrics(res: RunResult, control: RunResult | None = None) -> dict:
    N = res.cfg.n_agents
    n_t = np.array([r["n_contaminated"] for r in res.series])
    f_t = n_t / N
    T = len(n_t) - 1
    src = res.source
    secondary = [v for v in res.first_infected if v != src]

    # --- reach ------------------------------------------------------------
    radius = len(secondary) / (N - 1)                       # cumulative "attack rate" excl. source
    peak = float(f_t.max())
    t_peak = int(np.argmax(f_t))
    t_sat = NAN
    if n_t.max() >= 2:                                      # some spread happened
        t_sat = float(np.argmax(f_t >= 0.9 * peak))         # first round within 90% of peak prevalence

    # --- timing / hops -----------------------------------------------------
    fpt = np.array([res.first_infected[v] for v in secondary], dtype=float)
    hop = np.array([res.hops[v] for v in secondary if res.hops.get(v) is not None], dtype=float)
    d = np.array([res.dist[v] for v in secondary if not math.isnan(res.dist[v])], dtype=float)

    # --- persistence / recovery -------------------------------------------
    R = res.cfg.repair_round
    start = R if R is not None else 0
    after = n_t[start:]
    zero_idx = np.flatnonzero(after == 0)
    recovery_time = float(zero_idx[0]) if (R is not None and zero_idx.size) else NAN

    out = {
        "contagion_radius": radius,
        "n_secondary": len(secondary),
        "peak_prevalence": peak,
        "t_peak": t_peak,
        "t_saturation": t_sat,
        "t_first_spread": float(fpt.min()) if fpt.size else NAN,
        "mean_first_passage": float(fpt.mean()) if fpt.size else NAN,
        "median_first_passage": float(np.median(fpt)) if fpt.size else NAN,
        "max_hops": float(hop.max()) if hop.size else (0.0 if not secondary else NAN),
        "mean_hops": float(hop.mean()) if hop.size else NAN,
        "max_graph_distance": float(d.max()) if d.size else NAN,
        "final_prevalence": float(f_t[-1]),
        "persisted": bool(n_t[-1] > 0),
        "persistence_rounds": int((after > 0).sum()),      # rounds since repair (or since t=0) with >= 1 contaminated
        "recovered": bool(n_t[-1] == 0),
        "recovery_time": recovery_time,
        "clean_acc_final": res.series[-1]["clean_acc"],
        "clean_acc_mean": float(np.mean([r["clean_acc"] for r in res.series])),
        "total_messages": int(sum(r["messages"] for r in res.series)),
        "false_claims": int(sum(r["false_claims"] for r in res.series)),
        "llm_calls": res.llm_calls,
        "horizon": T,
    }
    out["false_claim_share"] = out["false_claims"] / out["total_messages"] if out["total_messages"] else NAN
    if control is not None:
        out["clean_acc_final_control"] = control.series[-1]["clean_acc"]
        out["clean_acc_delta"] = out["clean_acc_final"] - out["clean_acc_final_control"]
        out["control_max_contaminated"] = max(r["n_contaminated"] for r in control.series)
    return out
