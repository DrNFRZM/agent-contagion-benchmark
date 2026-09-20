"""Command line: `acb run --config configs/quick.yaml --out results/quick`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import load_spec
from .experiment import run_from_file


def _print_summary(tables: dict[str, pd.DataFrame]) -> None:
    s = tables["summary_topology"]
    cols = ["topology", "n_runs", "contagion_radius", "peak_prevalence", "mean_first_passage", "max_hops",
            "persisted", "recovered", "recovery_time", "clean_acc_delta"]
    with pd.option_context("display.width", 200, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print("\nSummary by topology (means of seed-level grid summaries; NaN = undefined for every run)")
        print(s[cols].to_string(index=False))
    ctrl = tables["runs"]["control_max_contaminated"].max()
    print(f"\nControl runs (no fault): max contaminated agents in any round = {int(ctrl)} (must be 0)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="acb", description="Topology-dependent fault contagion benchmark")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run an experiment spec (YAML)")
    r.add_argument("--config", required=True, type=Path)
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--no-figures", action="store_true")
    r.add_argument("--progress", action="store_true")
    sub.add_parser("version")
    args = p.parse_args(argv)

    if args.cmd == "version":
        from . import __version__
        print(__version__)
        return 0
    spec = load_spec(args.config)
    n_cells = len(spec.configs())
    backends = {c.backend for c in spec.configs()}
    print(f"experiment '{spec.name}': {n_cells} cells x {len(spec.seeds)} seeds "
          f"(+ paired no-fault controls); backend(s): {', '.join(sorted(backends))}")
    tables = run_from_file(args.config, args.out, figures=not args.no_figures, progress=args.progress)
    _print_summary(tables)
    print(f"\nwrote tables{'' if args.no_figures else ' and figures'} to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
