# results/

- `quick/` — the committed output of `configs/quick.yaml` (MockLLM, deterministic for the recorded environment, normally under one minute on one CPU core):
  run-level and per-agent tables, summaries with seed-clustered bootstrap intervals, five figures, and the verbatim console and
  pytest output captured when the files were generated.
- Everything else under `results/` (for example `results/full/`) is git-ignored: regenerate it with
  `acb run --config configs/full.yaml --out results/full`.

With Python 3.12 and `requirements-repro.txt`, regenerating `quick/` reproduces the numeric CSV contents (fixed seeds, no network).
Newline bytes can differ across operating systems, and figures can differ slightly across platforms or font renderers.
Generated with Python 3.12.14, numpy 2.5.3, pandas 3.0.6, networkx 3.6.1, matplotlib 3.11.2 and PyYAML 6.0.3.
