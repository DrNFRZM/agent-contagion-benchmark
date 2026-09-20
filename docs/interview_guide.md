# Interview guide

For explaining this project to a supervisor, admissions committee or interviewer. The rule for every answer: say what the
benchmark measures, what it does not, and what evidence would change your mind. The quick-run numbers quoted here come from a
mock backend, 8 agents and 5 seeds; they demonstrate that the instrument works, not what real LLM systems do.

---

## 1. Thirty-second explanation

"I built a small benchmark that plants one harmless false fact — say, a fictional planet's capital — in one agent's memory and
watches how it spreads through a network of LLM agents. I compare four communication structures: a central hub, a fixed pipeline,
a decentralised acyclic graph and a decentralised cyclic graph. I measure how far the false belief spreads, how quickly, whether
it survives after the original source is fixed, and whether it harms other answers. The goal is to test whether decentralisation
really reduces systemic risk or just changes how failures propagate."

## 2. Two-minute explanation

"Multi-agent LLM systems share information through messages and memory. If one agent's memory is wrong, either by accident or
because someone poisoned it, other agents may adopt the belief and pass it on. Whether that turns into a system-wide failure
should depend on the communication structure, not only on the agents. Decentralisation is often assumed to help because there is
no single point of failure, but a decentralised network also has more paths along which a bad belief can travel and be reinforced.

The benchmark uses synthetic facts about invented planets so that nothing harmful is involved. Each agent has local memory with
confidence values, simple retrieval, and a message history. An LLM backend decides which value an agent believes given its memory
and the messages it received. For tests and CI I use a deterministic mock that weighs evidence; real local or API models are optional.

One agent gets a false memory at time zero. Each round agents send each other claims along the edges. I track the fraction of
agents that give the false answer over time, the cumulative reach, first-passage times, the number of hops, and, after an
oracle repairs the source at round 10, how long contamination persists and whether the network recovers. Every run has a paired
no-fault control with identical random structure, which gives a clean estimate of side effects on unrelated answers.

The first demonstration, on the mock, shows the mechanics: in a star the location of the fault dominates — hub faults reach about
90% of agents, leaf faults about 3% — and memory policy matters: an overwrite-on-conflict policy left false beliefs in most pipeline and DAG runs after
repair, while keeping all evidence or expiring old items mostly recovered. I treat these as properties of the model, not of LLMs, and the next step is
running the same protocol with real models and matched network statistics."

## 3. Detailed experiment explanation

1. **World.** Eight facts of the form "The capital of Veloria is Arden." Fact 0 is the target. Every agent knows it truthfully; each other fact is known by an agent with probability 0.6 (and by at least one agent).
2. **Topology.** `star`, `pipeline`, `dag` (each node reads from two random earlier nodes), `graph` (Watts–Strogatz small world with bidirectional edges).
3. **Fault.** At t = 0 the source agent's true target entry is replaced by "Mira" with configured confidence 1.0 (stored at the memory cap, 0.99). The source is the highest-betweenness agent (`central`) or the lowest-betweenness agent with the largest reach (`peripheral`).
4. **Round.** Each edge is used with probability 0.7; a used edge carries two randomly chosen claims (the sender's belief and confidence). Receivers call the backend once per fact with mail, listing retrieved memory and messages with weights (sender confidence × trust 0.7). Accepted evidence is written or reinforced; a retention policy then deletes rivals (`overwrite`), expires learned items (`ttl`), or keeps everything (`keep_all`).
5. **Probe.** After each round every agent answers every fact from memory alone. "Contaminated" means answering "Mira" for the target.
6. **Repair.** At round 10 the source's false entry is replaced by the truth. Rounds continue to 30.
7. **Control.** Same seed, no fault. The control must show 0 contaminated agents (it is asserted and printed), and the difference in clean accuracy is the spillover estimate.
8. **Analysis.** Run-level metrics, seed-level aggregation with bootstrap intervals, spread by distance from the source, and correlations of reach with degree, betweenness and distance. Repeated grid cells are averaged within a seed before resampling.

## 4. Why decentralisation?

Centralised orchestration has an obvious single point of failure and an audit point; decentralised designs avoid the bottleneck and
may be more scalable and robust to node loss. But results from distributed systems and network science on contagion suggest that removing the hub does not remove propagation; it may redistribute it. For LLM agents there is
an additional twist — the "components" are probabilistic, share training data and often share a base model, so failures can be correlated,
and information is transmitted as natural language that agents tend to trust. The empirical question is which effect dominates for
belief errors in memory.

## 5. Why memory poisoning?

Memory is what turns a one-off error into a persistent one. A hallucination in a single answer is transient; the same content written to
long-term memory is retrieved repeatedly, re-shared and reinforced. It is also a natural attack surface (anything an agent reads may be
written to memory) and a natural fault surface (stale or corrupted records). Studying it with harmless synthetic facts isolates the
propagation mechanics from any harmful content.

## 6. Accidental fault vs adversarial fault

- **Accidental**: not chosen to maximise damage; random location, no adaptation, no targeting of high-influence nodes. Analysed with
  reliability tools (failure rates, mean time to recovery).
- **Adversarial**: chosen location and timing, crafted wording, possibly repeated and adaptive to defences; analysed with security tools
  (threat models, worst-case guarantees, game-theoretic reasoning).
- **In this benchmark** the injected entry is the same in both cases, so the results are a non-adaptive baseline. Within the same
  one-shot capability and for a fixed damage metric, an informed adversary could select a worse location than a uniformly random
  fault—for example, the star hub. That observation does not make these runs a bound on richer adaptive attacks. The framing
  separates "how fragile is the structure" from "how capable is the attacker".

## 7. Why topology matters

Topology constrains who can influence whom (reach), how quickly (path length), through how many independent routes (redundancy, which both
spreads a false belief and can correct it), and whether information can return to its origin (cycles, which allow reinforcement).
The same agents in a star and in a pipeline can produce very different contagion from the same fault. It is also a design variable that
practitioners control directly, which makes results actionable.

## 8. What is a DAG?

A directed acyclic graph: edges have a direction and no path returns to its starting node. In a DAG-structured agent system information
flows only forward, so a fault can only affect *descendants* of its origin; there is no feedback, so a downstream agent cannot correct an upstream one. The pipeline is the
simplest DAG (a path). In this benchmark the tests assert that pipeline contamination stays in the source's descendants. A DAG has a topological order, so "upstream/downstream" is well defined.

## 9. What does contagion radius mean?

The fraction of the other agents that were ever contaminated: (agents other than the source that ever answered the false value) / (N − 1).
It is cumulative reach, like the "attack rate" in epidemiology, and does not say whether they are still contaminated. Related but different:
*prevalence* (fraction contaminated at a given time), *peak prevalence*, and *hop distance* (how far away in the graph). A radius of 0.9 means nearly everyone was affected at some point.

## 10. Confounders

- Degree, path length, cyclicity, directionality and source reach change together when you change the topology label.
- "Central" and "peripheral" are defined differently in different graphs.
- Hand-set trust and confidence parameters.
- Random graph draw (dag, graph) vs deterministic graph (star, pipeline).
- Network size, which changes reach and path length.
- Retention policy, which interacts with topology.

Mitigations: report network measures with every run, use paired controls, common random numbers, fault-location factor, degree-matched
variants and sensitivity sweeps (planned).

## 11. Validity threats

- **Construct**: "contaminated" = one probe answer; real belief is richer.
- **Internal**: possible implementation bugs (mitigated by 53 tests including invariants); tie-breaking rules; attribution of infections to senders.
- **External**: synthetic facts, mock model, small networks, honest channels, synchronous rounds.
- **Statistical**: few seeds; cells share seeds, so they are correlated; bootstrap over seeds, not over runs within a seed.
- **Conclusion**: the mock encodes assumptions about evidence weighting that drive results; conclusions about LLMs need real-backend replication.

---

## 12. Twenty hard questions (and answers)

**1. Your mock is a weighted vote. Why should anyone care about its results?**
For what the structure can do under a simple, transparent reconciliation rule. It lets me test the instrument (metrics, controls,
invariants) exactly. It does not tell us how LLMs reconcile evidence; that requires real-backend runs, which the interface supports but
which are not in this release.

**2. Is contagion here a property of topology or of the agents' update rule?**
Both, jointly. That is why I vary retention policy and roles too. To isolate topology I hold the rule fixed and compare structures;
to isolate the rule I hold the structure fixed. The quick run shows retention has effects of comparable size to topology
in some cells; the full grid and a variance decomposition (planned) would quantify it.

**3. Topologies differ in degree and path length. What did you actually vary?**
A bundle of properties. I cannot claim that "cycles" or "centralisation" is the cause. The next step is degree-matched controls (for example
a DAG and a cyclic graph with equal mean degree and source reach) and regressions with network measures as covariates. I already record those measures per run.

**4. Why is a fault at the star's hub so much worse than at a leaf?**
My working explanation, not yet isolated by an ablation: a hub fault is relayed to every other agent in one hop, and a false claim
with weight 0.7 beats a worker's seeded true memory (confidence 0.6). A leaf fault must first flip the hub, and the hub receives true claims from the
other leaves every round, which raises its confidence in the truth above the weight of a single false claim; the leaf's message has to win that race. This depends on my trust assumptions
(`hub_trust` = `peer_trust` by default). If workers trusted the orchestrator more, or the orchestrator verified less, the leaf case could get worse; untested.

**5. Doesn't the retention result ("overwrite persists") just reflect a design choice that deletes the truth?**
Yes; that is the mechanism I believe is at work, and it is a legitimate finding about a design choice (last-writer-wins memory removes the
fallback), not a discovery about LLMs. It says memory policy can matter more than topology for persistence in this model.

**6. Is a five-seed experiment evidence of anything?**
Not of population effects. It shows that the measurement pipeline works and gives rough magnitudes. The seed-clustered intervals are
unstable with five resampling units. The full spec has 10 seeds per cell and several sizes; a confirmatory study would preregister the
hypotheses and use more (H1 currently specifies at least 30).

**7. How do you know the code is correct?**
Unit tests for memory policies, the mock rule, topology generators and metrics computed by hand; simulation invariants (exactly one contaminated
agent at t = 0; controls never contaminated; pipeline contamination confined to descendants; determinism; no spread at zero communication; fault and control
share random structure). These do not prove correctness, but they cover the main failure modes I could think of.

**8. Why paired controls?**
Because the clean-accuracy baseline is not 1 (agents start with partial knowledge and learn it through messages), so the effect of the fault
on other facts is the *difference* from a same-seed run without a fault. Common random numbers also cut variance in comparisons.

**9. Why is `clean_acc_delta` zero?**
By construction in the mock: the fault concerns one fact and nothing couples facts except the `bounded` capacity. It is a sanity check and a
placeholder for real models, where cross-fact interference is plausible. I do not claim the absence of spillover in real systems.

**10. Your graph recovered fastest, contradicting the "cycles cause echo chambers" story. Do you believe it?**
Only as a statement about this parameter setting: dense bidirectional neighbourhoods also re-inject the truth every round, and truth
starts with the majority. Echo chambers need a locally self-reinforcing false subgraph, for example if the source's neighbours are also highly confident or
clustered. I would test with clustered graphs, higher injected confidence, and lower base confidence.

**11. Why not use LangChain / AutoGen / CrewAI?**
Because the message flow is the independent variable, and I want every step to be inspectable. It also keeps the codebase small.
The cost is fewer realistic behaviours. A natural extension is to replay the topologies inside one of those frameworks and compare.

**12. What is your definition of persistence and why the repair?**
Persistence = contamination present at the horizon, and rounds with contamination after repair. Without a repair event a false belief in a
non-recovering system simply stays; the repair asks whether the network *heals* once the root cause is fixed. The repair is an oracle, which is unrealistic;
real systems need detection.

**13. What would falsify your main hypotheses?**
For H1: no larger hub–leaf gap in the star than in the graph (the paired difference-in-differences interval includes 0). For H2: cyclic topologies not persisting more
than acyclic under matched conditions. For H3: topology explaining more persistence variance than retention. All are written down in the research note before running the full grid.

**14. How does this relate to prompt-injection worms and memory-poisoning attacks in the literature?**
It is a stripped-down, harmless abstraction of them: one bad belief, honest channels, no adaptation. Attack papers study how to craft
payloads that succeed against particular models; this benchmark studies what the *network* does with a successful injection. The two are
complementary; a thesis could combine an attack model with the topology analysis. The roadmap links the primary papers that motivate this distinction.

**15. What if the real LLM is stubborn or gullible? Does your setup capture that?**
Only via roles and the weights in the mock (verifier, relay). With a real backend, gullibility becomes an emergent property that I would
*measure*: run the same spec on the mock and on the model, and fit effective weights from the observed decisions.

**16. Why single-token synthetic facts? Doesn't that make retrieval trivial?**
It makes contamination unambiguous to score and avoids pre-training knowledge leakage. Retrieval is deliberately simple; harder retrieval (embeddings, noisy
queries) is a separate factor that could be added, at the cost of confounding.

**17. Could a defence change the picture?**
Yes, and it is the obvious next experiment: quorum acceptance (k of m sources), provenance tracking, trust learning, periodic verification against a trusted source.
Their effect probably depends on topology (quorum is impossible in a pipeline with in-degree 1), which is itself a design lesson.

**18. Does scaling N change the story?**
Probably: reach and path length change with N; contagion may saturate faster in small worlds. The full grid includes N = 8, 16, 32 to test this, but the
current results are at N = 8 only, which is too small to say anything about scaling.

**19. What would you do first with a real model?**
A small pilot: 8 agents, 3 topologies, 3 seeds, a small open model at temperature 0, same YAML. Check that the parse rate is high, that the agent decisions correlate with
the mock's weighting, then compare radius/persistence. If the parse rate or determinism is poor, fix that before interpreting anything.

**20. What is the contribution beyond "run a simulation"?**
A reusable, small, safe instrument with clear definitions (radius, first-passage, persistence, recovery, spillover), paired controls, tested invariants, a
falsifiable protocol and explicit threat model. The scientific contribution has to come from the thesis: running it on real agents with matched network structure and
adversarial fault models. I would not present the current repository as a result.

---

## 13. Things not to say

- "This proves decentralised systems are less secure/more secure." It does not.
- "The results generalise to GPT/Claude/Llama agents." They were not run on them.
- "The star is worst." Only when the fault is at the hub, in this model, with these parameters.
- Quote a number without its seeds, network size and backend.
