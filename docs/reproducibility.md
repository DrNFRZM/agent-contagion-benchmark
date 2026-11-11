# Reproducing the mock experiment

## 11 November 2026 maintenance verification

The AI-assisted maintenance pass used Python 3.12.16 on Windows with NumPy
2.3.5, pandas 2.2.3, NetworkX 3.7, PyYAML 6.0.3, and Matplotlib 3.10.8.
The shared audit environment passed its dependency consistency check.

All 53 tests passed. A fresh quick run completed 120 fault runs and their
paired no-fault controls. All seven CSV outputs matched the committed tables
within relative/absolute tolerance 1e-12: 120 run rows, 960 agent rows,
3,720 time-series rows, 24 cell summaries, four topology summaries, four
centrality/exposure rows, and 14 spread-by-distance rows. No-fault contamination
remained zero. Figures were generated, but PNG byte equality was not required.

Outputs were stored in a separate local verification directory. Original result
artifacts were retained. No real LLM, HuggingFace weights, API endpoint, or
paid service was used; the findings remain confined to this deterministic mock.

## Earlier verification record

Installation and execution were checked in a fresh Python 3.12.14 virtual
environment on Linux, CPU only. `pip install -e ".[dev]"` and `pip check`
completed successfully. This environment resolved NumPy 2.5.4, pandas 3.0.6,
NetworkX 3.7, Matplotlib 3.11.2, and PyYAML 6.0.3.

`python -m pytest` passed all 53 tests. A fresh
`acb run --config configs/quick.yaml --out /tmp/acb-verification` completed
120 fault runs with their paired controls and produced the tables and figures.

The fresh CSVs were compared with `results/quick/`: runs, agents, time series,
topology and cell summaries, spread by distance, and centrality exposure.
Row counts and columns agreed, and every numerical field matched within a
relative and absolute tolerance of 1e-12. The no-fault controls again had zero
contaminated agents.

NetworkX and NumPy differ from the versions recorded for the committed run;
that did not change these numerical outputs. Rendered PNG bytes were not used
as an equality test. `requirements-repro.txt` retains the original direct
dependency versions for repeating that environment.

This check used the deterministic mock reader. It did not execute the optional
HuggingFace or API adapters, or validate conclusions about real LLM agents.
