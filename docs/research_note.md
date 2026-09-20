# Research note: topology and fault contagion

*Status: protocol and instrument. Only the quick, mock-backend demonstration has been run.*

## 1. Question

How does communication topology affect the **propagation, persistence and recovery** of one injected false memory in a
multi-agent LLM system? The broader thesis question is whether decentralisation reduces systemic risk or merely changes
how failures propagate. This note does not answer that; it defines what an answer would need.

## 2. Hypotheses

Each hypothesis is stated so that it can fail.

**H1 — Fault location dominates in hub-centred topologies.** In `star`, the contagion radius of a hub fault exceeds that of a
leaf fault by a wider margin than the corresponding central-vs-peripheral gap in `graph`.
*Not supported if* a paired, seed-level difference-in-differences of mean radius, over ≥ 30 seeds and all tested N, has a 95%
bootstrap interval that includes 0; *falsified in the stronger sense* if that interval lies below 0. The supplied full grid has
10 seeds and is exploratory, so it does not meet this confirmatory criterion.

**H2 — Cycles sustain contamination.** With the source repaired, the probability of contamination at the horizon is higher in
cyclic topologies (`graph`, `star`) than in acyclic ones (`dag`, `pipeline`), holding retention policy, N, and p fixed.
*Not supported if* a paired, seed-level 95% bootstrap interval for P(persisted | cyclic) − P(persisted | acyclic) includes 0
across matched cells; *falsified in the stronger sense* if the interval lies entirely below 0.
*Preliminary evidence (quick run, 5 seeds, N = 8) is mixed:* `star` (0.37) persisted more than `dag` (0.30) and `pipeline` (0.27), but `graph`, the other cyclic topology, had the lowest persistence (0.07). The acyclic persistence was driven mainly by `overwrite` retention. Not conclusive.

**H3 — Memory retention matters at least as much as topology for persistence.** Retention policy explains at least as much
variance in persistence as topology does.
*Falsified if* a preregistered factorial analysis appropriate to the outcome (for example, logistic modelling for `persisted` and
a count model for persistence rounds) assigns a larger, stable effect to topology than retention across the full grid. This analysis
is planned, not implemented; the current marginal plots are not a test of H3.

**H4 — Spillover is negligible without capacity pressure.** `clean_acc_delta` is 0 for policies without eviction and can be
negative only under `bounded` memory (or, for real LLMs, through genuine cross-fact interference).
*Sanity check for the mock; the interesting version is on real backends.*

## 3. Variables

| Role | Variable | Levels (quick / full) |
|---|---|---|
| Independent | topology | star, pipeline, dag, graph |
| Independent | number of agents N | 8 / 8, 16, 32 |
| Independent | retention policy | keep_all, overwrite, ttl / + bounded |
| Independent | communication probability p | 0.7 / 0.3, 0.6, 1.0 |
| Independent | role mix | homogeneous / homogeneous, heterogeneous (50% worker, 25% verifier, 25% relay) |
| Independent | fault location | central, peripheral |
| Controlled | facts (8), claims per message (2), trust (0.7), base confidence (0.6), injected confidence (1.0), coverage (0.6), rounds, repair round | fixed per spec |
| Random | topology draw (dag, graph), edge use per round, claim selection, coverage, roles | seeded; fault/control pairs share draws; seed labels are reused across cells, but draws do not map one-to-one when topology or size changes |
| Dependent | metrics below | |

Also available but not in the grids: `fanout` (gossip to k neighbours), `hub_trust`, `dag_in_degree`, `ws_k`, `ws_beta`, `ttl`, `capacity`, `injected_conf`, `peer_trust`, `base_conf`.

## 4. Metrics

Notation: N agents, source s, n_t = agents whose memory-only answer to the target question is the false value after round t (t = 0 is right after injection), f_t = n_t / N, R = repair round, T = horizon.

| Metric | Definition |
|---|---|
| **Prevalence** f_t | n_t / N |
| **Contagion radius** | (number of agents other than s ever contaminated) / (N − 1). Cumulative reach ("attack rate") |
| Peak prevalence | max_t f_t |
| **First-passage time** | for each reached agent v ≠ s, the first t with v contaminated; reported as mean / median over reached agents and `t_first_spread` = min |
| **Time to saturation** | first t with f_t ≥ 0.9 · max f, defined only if some spread occurred (n_t ≥ 2 at some t) |
| **Hops** | `max_hops`: depth of the infection tree (a newly contaminated agent is one hop beyond the nearest contaminated sender of a false claim that round). `max_graph_distance`: largest shortest-path distance from s among reached agents |
| **Persistence** | `persisted` = n_T > 0; `persistence_rounds` = number of rounds t ≥ R with n_t > 0 |
| **Recovery** | `recovered` = n_T = 0; `recovery_time` = (first t ≥ R with n_t = 0) − R, undefined if never |
| **Clean-task accuracy** | mean over agents and the N_f − 1 clean facts of [answer = truth]; unknown counts as wrong. `clean_acc_delta` = fault run − paired control at the horizon |
| Communication | total claims delivered, false target claims delivered, LLM calls |
| **Topology-specific spread** | `spread_by_distance` (fraction reached vs directed distance from s), `centrality_exposure` (Spearman correlation of reach with degree, in-degree, betweenness, distance), and per-run network measures. Mean degree is mean total directed degree (in + out); path length and diameter use reachable ordered node pairs only. |

## 5. Protocol

1. Build the topology from the seed. Assign roles and seeded knowledge (every agent knows the target fact truthfully; each clean fact is known with probability `coverage`, and by at least one agent).
2. Choose the source by `fault_location`. Replace its true target entry by the false one (confidence 1.0).
3. For rounds 1..T: (optional) repair at R → sample which edges are used (probability p) and which claims they carry → deliver claims → each receiver reconciles memory with its inbox via the LLM backend → retention policy → probe all agents on all facts.
4. Repeat with `fault = false` and the same seed (paired control; identical random structure).
5. Compute the metrics. For a marginal summary, first average repeated grid cells within each seed, then form a 95% percentile
   bootstrap interval over those seed-level means (2,000 resamples, fixed bootstrap seed). A fully specified cell has one run per seed.
6. Report every cell, including nulls; report the fraction of runs in which a metric is undefined (e.g. recovery time for runs that never recovered).

## 6. Interpretation guidelines

- Compare topologies **within the same cell of the other factors**, and report differences with CIs, not p-values on tiny samples.
- The quick run has only five resampling units. Its intervals are descriptive and unstable, not confirmatory evidence.
- Radius and persistence are properties of *(topology, location, retention, parameters)* jointly. A statement such as "topology X is more robust" needs qualifying with all of these.
- Undefined values (`NaN`) are not zeros: `mean_first_passage` is over reached agents only, `recovery_time` over runs that recovered only. Always read them together with radius and `recovered`.
- With the mock, differences arise from the evidence-weighting rule, the confidence bookkeeping, and the network. They say what the *structure* can do under a simple reconciliation rule, not how an LLM behaves.
- A result on a real backend must be compared with the mock under the same spec before being attributed to the model.

## 7. Confounders and validity threats

- **Structural confounding.** Topologies differ simultaneously in mean degree, path length, reach of the source, cyclicity, and directionality (quick run: mean degree 1.75 pipeline / 3.25 dag / 3.5 star / 8.0 graph). Comparing labels does not isolate any single property. Mitigation: add degree-matched variants and report network measures as covariates.
- **Location confound.** "Central" and "peripheral" mean different things in each topology (see `pick_source`). Mitigation: report both and `random`.
- **Trust and confidence parameters** were set by hand; effects can flip when they change. Mitigation: sensitivity sweeps over `peer_trust`, `base_conf`, `injected_conf` (fields exist; not yet swept).
- **Small N and few seeds.** N = 8 and 5 seeds in the quick run.
- **Construct validity.** "Contaminated" is a memory-only *answer* to one probe question; real systems may hold a false belief but answer differently under another prompt.
- **External validity.** Synthetic single-token facts, honest channels, synchronous rounds, one fact under attack.
- **Mock realism.** Real LLMs are noisy, context-length-sensitive and order-sensitive; the mock is none of these.
- **Metric artefacts.** Saturation time depends on the 90% threshold; `max_hops` depends on the tie-breaking rule for attributing infections.

## 8. Falsification of the framing itself

The core premise ("topology matters for contagion of a false belief") would be undermined if, on a real backend with matched
network measures, radius and persistence show no dependence on topology beyond what mean degree and source reach explain.
