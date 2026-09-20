# Learning roadmap

A suggested path from this repository to an MSc thesis and a PhD application. Times are rough and assume part-time work.

## Stage 0 — Understand and extend this repository (weeks 1–2)

- Read `simulation.py`, `memory.py`, `metrics.py` end to end; predict a run by hand on a 4-node pipeline.
- Change one parameter at a time (`peer_trust`, `base_conf`, `injected_conf`, `comm_prob`) and explain each change in the curves.
- Run `configs/full.yaml` (or a subset) as an exploratory sweep. Do not call its 10 seeds a confirmatory test of H1, whose written criterion requires at least 30.
- Implement a preregistered factorial analysis suited to each outcome (for example, logistic modelling for `persisted`) rather than inferring H3 from marginal bar charts.

## Stage 1 — Network science and spreading processes (weeks 2–5)

Concepts: degree, betweenness, path length, small-world and scale-free graphs, DAGs, cycles; SIR/SIS epidemic models, threshold
and complex contagion, DeGroot consensus, voter model. Exercise: reproduce a threshold-model cascade on the four topologies in 50 lines and compare with this simulator's behaviour.

Suggested foundational reading:
- Newman, *Networks* (textbook).
- Watts & Strogatz (1998), small-world networks.
- Barabási & Albert (1999), scale-free networks.
- Pastor-Satorras & Vespignani (2001), epidemic spreading in scale-free networks.
- Granovetter (1978), threshold models of collective behaviour; Centola & Macy (2007), complex contagion.
- DeGroot (1974), reaching a consensus.
- Kempe, Kleinberg & Tardos (2003), influence maximisation.

## Stage 2 — Distributed systems and reliability (weeks 4–7)

Concepts: fault vs failure, fail-stop vs Byzantine faults, quorum, replication, gossip protocols, eventual consistency, mean time to recovery.
Suggested reading: Lamport, Shostak & Pease (1982) Byzantine Generals; Castro & Liskov (1999) PBFT; a survey chapter on gossip/epidemic protocols.
Question to answer: which distributed-systems defences (quorum, verification) map to LLM agents, and which fail because agent errors are correlated?

## Stage 3 — LLM agents, memory and security (weeks 6–10)

Areas to survey: LLM multi-agent frameworks and their communication structures; memory and retrieval-augmented agents; indirect prompt injection;
memory- and knowledge-base poisoning; self-propagating attacks between agents; topology-aware safety studies of multi-agent networks.
Primary starting points:

- Greshake et al. (2023), [*Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*](https://arxiv.org/abs/2302.12173).
- Zou et al. (2024), [*PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models*](https://arxiv.org/abs/2402.07867).
- Chen et al. (2024), [*AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases*](https://arxiv.org/abs/2407.12784).
- Lee and Tiwari (2024), [*Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems*](https://arxiv.org/abs/2410.07283).
- Gu et al. (2024), [*Agent Smith: A Single Image Can Jailbreak One Million Multimodal LLM Agents Exponentially Fast*](https://arxiv.org/abs/2402.08567).
- Yu et al. (2024), [*NetSafe: Exploring the Topological Safety of Multi-agent Networks*](https://arxiv.org/abs/2410.15686).
- Zhuge et al. (2024), [*GPTSwarm: Language Agents as Optimizable Graphs*](https://arxiv.org/abs/2402.16823).

Frameworks such as AutoGen, CAMEL and MetaGPT are useful implementation comparisons, but their documentation is not evidence for a security claim.
Deliverable: a two-page table of what each paper measures, its threat model, and where "topology" enters. Identify the gap this benchmark could fill.

## Stage 4 — Experimental methodology (weeks 8–12)

Preregistration, effect sizes with intervals, common random numbers, ablations, sensitivity analysis, negative results. Practise on this repository: write the
analysis plan for the full grid *before* running it, then run it and report deviations.

## Stage 5 — Real-model study (months 3–5)

1. Pilot with a small open model through the HF backend (temperature 0): parse rate, determinism, agreement with the mock.
2. Add a "gullibility calibration" step: estimate effective evidence weights from the model's decisions and feed them back into the mock.
3. Run 3–4 topologies × 2 sizes × 5+ seeds with matched network statistics.
4. Report differences from the mock explicitly.

## Stage 6 — Thesis extensions (months 4–9)

- Degree-matched and clustered topologies to isolate structure (regression with network measures as covariates).
- Defences: quorum acceptance, provenance, trust learning, periodic verification; test how their benefit depends on topology.
- Adaptive fault model: attacker chooses location and timing; compare with random faults.
- Dynamic and hierarchical topologies (rewiring, supervisor trees), asynchronous rounds.
- Multiple simultaneous faults and correlated failures (shared base model).
- Retrieval realism: embedding retrieval, noisy queries, larger memories.

## Stage 7 — PhD-application packaging (final months)

- One clean repository, one short paper-style report (4–6 pages), reproducible figures, honest limitations.
- A one-page research statement: question, what the benchmark established, what it did not, and the plan.
- Practise the [interview guide](interview_guide.md), especially the "what would falsify this" and "what is your contribution" answers.
