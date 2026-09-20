from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from acb.analysis import bootstrap_ci, summarize
from acb.cli import main
from acb.config import load_spec
from acb.experiment import run_experiment

ROOT = Path(__file__).resolve().parents[1]


def tiny_spec(tmp_path):
    p = tmp_path / "tiny.yaml"
    p.write_text(yaml.safe_dump({
        "name": "tiny", "seeds": [0, 1],
        "base": {"n_agents": 6, "rounds": 12, "repair_round": 5},
        "grid": {"topology": ["star", "pipeline", "dag", "graph"], "retention": ["keep_all", "ttl"]},
    }))
    return p


def test_shipped_configs_load_and_use_mock_only():
    for name in ("quick", "full"):
        spec = load_spec(ROOT / "configs" / f"{name}.yaml")
        cfgs = spec.configs()
        assert cfgs and {c.backend for c in cfgs} == {"mock"}
    assert len(load_spec(ROOT / "configs" / "quick.yaml").configs()) == 24


def test_unknown_field_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump({"name": "x", "seeds": [0], "base": {"nonsense": 1}, "grid": {}}))
    with pytest.raises(ValueError, match="unknown config fields"):
        load_spec(p).configs()


def test_invalid_seed_and_grid_specs_rejected(tmp_path):
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(yaml.safe_dump({"name": "x", "seeds": [0, 0], "base": {}, "grid": {}}))
    with pytest.raises(ValueError, match="unique"):
        load_spec(duplicate)

    empty = tmp_path / "empty.yaml"
    empty.write_text(yaml.safe_dump({"name": "x", "seeds": [0], "base": {}, "grid": {"topology": []}}))
    with pytest.raises(ValueError, match="non-empty lists"):
        load_spec(empty)


def test_run_experiment_tables(tmp_path):
    t = run_experiment(load_spec(tiny_spec(tmp_path)))
    runs, ts, ag = t["runs"], t["timeseries"], t["agents"]
    assert len(runs) == 4 * 2 * 2
    assert (runs["control_max_contaminated"] == 0).all()
    assert set(ts["t"]) == set(range(13)) and len(ag) == len(runs) * 6
    assert runs["contagion_radius"].between(0, 1).all()
    assert (ag[ag["is_source"]]["first_passage"] == 0).all()


def test_cli_end_to_end_writes_outputs(tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["run", "--config", str(tiny_spec(tmp_path)), "--out", str(out)]) == 0
    for f in ("runs.csv", "timeseries.csv", "agents.csv", "summary_topology.csv", "spread_by_distance.csv",
              "fig_networks.png", "fig_curves.png", "fig_topology_comparison.png", "fig_spread_by_distance.png",
              "fig_breakdown_retention.png"):
        assert (out / f).stat().st_size > 0, f
    assert "must be 0" in capsys.readouterr().out
    s = pd.read_csv(out / "summary_topology.csv")
    assert set(s["topology"]) == {"star", "pipeline", "dag", "graph"}


def test_bootstrap_ci_deterministic_and_brackets_mean():
    x = np.array([0.0, 1.0, 0.0, 1.0, 1.0, np.nan])
    lo, hi = bootstrap_ci(x)
    assert (lo, hi) == bootstrap_ci(x) and lo <= np.nanmean(x) <= hi


def test_summary_bootstraps_seed_level_means():
    # Each seed is a cluster containing two deliberately different cells. The
    # point estimate must give the two seeds equal weight.
    runs = pd.DataFrame({
        "topology": ["star"] * 4,
        "seed": [0, 0, 1, 1],
        "score": [0.0, 0.0, 1.0, 1.0],
    })
    s = summarize(runs, ["topology"], metrics=["score"]).iloc[0]
    assert s["n_runs"] == 4 and s["n_seeds"] == 2
    assert s["score"] == pytest.approx(0.5)
    assert s["score_lo"] == 0.0 and s["score_hi"] == 1.0


def test_no_secret_like_strings_in_repo():
    import re
    pat = re.compile(
        r"\bsk-[A-Za-z0-9_-]{20,}|\bhf_[A-Za-z0-9]{20,}|\bghp_[A-Za-z0-9]{20,}|"
        r"\bgithub_pat_[A-Za-z0-9_]{20,}|BEGIN [A-Z ]*PRIVATE KEY|\bAKIA[0-9A-Z]{16}"
    )
    skipped = {
        ".git", ".venv", "venv", "env", ".tox", ".nox", "__pycache__",
        ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist",
    }
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & skipped) and p.suffix in {
            ".py", ".yaml", ".yml", ".md", ".toml", ".csv", ".txt", ".cff"
        }:
            assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f"secret-like string in {p}"
