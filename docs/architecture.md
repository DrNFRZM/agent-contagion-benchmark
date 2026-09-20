# Architecture

## Modules

```
cli.py ──► experiment.py ──► simulation.simulate(cfg, seed, fault) ──► RunResult
              │                    │  uses
              │                    ├─ topology.py   build graph, choose source, network measures
              │                    ├─ agent.py      Agent: memory + LLM calls + trust + history
              │                    │     ├─ memory.py  items, noisy-OR reinforcement, retrieval, retention policies
              │                    │     └─ llm/       LLMBackend: mock | hf | api (+ prompt format, answer parser)
              │                    └─ facts.py      synthetic world (invented planets)
              ├──► metrics.compute_metrics(run, control)
              ├──► analysis.py   summaries, seed-clustered intervals, spread-by-distance, centrality exposure
              └──► viz.py        matplotlib figures
config.py: RunConfig (one run) and ExperimentSpec (YAML: base + grid + seeds)
```

## One round

```
t-1 beliefs ──► send ──► inbox ──► absorb (1 LLM call per fact with mail) ──► retention ──► probe (N x facts LLM calls) ──► t beliefs
```

1. **Repair** (only at `repair_round`, only in fault runs): the source's injected entry is removed and the true entry re-inserted.
2. **Send.** For each agent u and each out-neighbour v (all, or `fanout` random ones): draw use ~ Bernoulli(`comm_prob`) and draw `message_facts` fact ids. If the edge is used, u sends its previous-round belief for each drawn fact together with its memory confidence. Unknown facts are not sent.
3. **Absorb.** Receiver v groups its inbox by fact. For each fact one LLM call is made with `MEMORY` (retrieved items with confidence) and `MESSAGES` (claims with weight = sender confidence × v's trust in the sender). The reply is parsed to a candidate value. Messages that support the answer are written or reinforced in memory (`learned`); others are dropped. `overwrite` then deletes rival items for that fact.
4. **Retention.** `ttl` expires learned items unreinforced for more than `ttl` rounds; `bounded` evicts lowest-confidence, oldest items beyond capacity.
5. **Probe.** Every agent answers every fact from memory only (no messages). This produces the metrics *and* is the content of next round's messages, so each round costs N × n_facts probe calls plus at most one call per (agent, fact) with mail.

## Prompt format (all backends)

```
system: You are agent A3 in a small team that keeps notes about fictional planets. ROLE: verifier. <role description>
user:   QUESTION: What is the capital of Veloria?
        MEMORY:
        - conf=0.60 :: The capital of Veloria is Arden.
        MESSAGES:
        - weight=0.70 :: The capital of Veloria is Mira.
        Answer with the single value only. Use the notes weighted by conf/weight. If nothing supports an answer, reply UNKNOWN.
```

The reply is mapped to one of the candidate values that appeared in the prompt (earliest mention); anything else counts as UNKNOWN. This makes hallucinated values harmless for the bookkeeping.

## Mock rule

For the asked fact, per candidate value: `w_mem · Σ conf(memory lines) + w_msg · Σ weight(message lines)`; largest wins; ties go to the value listed first (older memory). Roles set `(w_mem, w_msg)`: worker/orchestrator (1, 1), verifier (1.5, 0.75), relay (0.75, 1.25). UNKNOWN when nothing matches.

## Randomness and pairing

Four independent numpy streams per seed (`topology`, `communication`, `setup`, `source`). None of the draws depends on belief content, so a fault run and its control with the same seed share the topology, roles, knowledge, edge usage and claim selection; they differ only through the injected fault. The control is cached across `fault_location` values because the location does not exist without a fault. Seed labels are also reused across grid cells, but differing graph shapes and sizes consume draws differently, so this is not exact event-level pairing between every pair of cells.

## Outputs of a run (`acb run`)

`runs.csv` (one row per fault run: config, network measures, all metrics), `timeseries.csv` (per run and round), `agents.csv` (per run and agent: role, degree, betweenness, distance from source, first-passage time), `summary_topology.csv`, `summary_cells.csv`, `spread_by_distance.csv`, `centrality_exposure.csv`, and the PNG figures. Summary intervals resample seed-level means rather than treating repeated grid cells as independent runs.

## Extending

- **New topology**: add a branch in `topology.build_topology`, add its name to `TOPOLOGIES` and a style in `viz.TOPO_STYLE`.
- **New backend**: subclass `LLMBackend.generate(system, prompt) -> str`, register in `llm.make_backend`.
- **New retention policy**: add to `memory.POLICIES` and handle it in `Memory.resolve` / `Memory.end_of_round`.
- **New metric**: add to `metrics.compute_metrics`; add it to `analysis.KEY_METRICS` to get CIs.

## Cost accounting

A quick-size run (8 agents, 8 facts, 30 rounds) makes about 2,200–3,000 LLM calls, reported as `llm_calls` in `runs.csv`. The full grid scales roughly linearly in N.
