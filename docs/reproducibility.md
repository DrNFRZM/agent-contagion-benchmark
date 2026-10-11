# Reproducing the mock experiment

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
