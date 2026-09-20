# Design decisions

Each entry: the choice, the main alternative, and the cost of the choice.

**1. Orchestration written from scratch, `networkx` only for graphs.** The object of study is the message flow; hiding it
in LangChain/CrewAI/AutoGen would hide the variable. *Cost:* the agents are simpler than in production frameworks, so
external validity is limited.

**2. Synchronous rounds.** All agents send from the previous round's state, then all update. *Alternative:* asynchronous
event-driven updates. Synchronous makes first-passage times and hops well defined and runs reproducible. *Cost:* real systems
are asynchronous; latency effects are absent.

**3. Belief = the LLM's memory-only answer.** Contamination is defined behaviourally, not by inspecting memory. *Why:* it is
what a downstream user would see, and it works for any backend. *Cost:* sensitive to the probe prompt and retrieval.

**4. Reconciliation is an LLM call, bookkeeping is code.** The backend decides *which value wins*; the agent code only writes
accepted evidence and applies the retention policy. *Why:* the interesting decision is delegated to the model, and swapping the
backend changes only that decision. *Cost:* a real model may output text that needs parsing; handled by candidate matching.

**5. Confidence with noisy-OR reinforcement.** Repeated agreeing evidence raises confidence towards a cap (0.99). *Alternative:*
counters or Bayesian updates. Noisy-OR is one line, monotone, and produces the "repeated exposure matters" dynamic. *Cost:* an
arbitrary model choice; sensitivity to `base_conf`, `peer_trust`, `injected_conf` is unexplored.

**6. MockLLM as an explicit weighted vote.** A transparent rule beats a fake "LLM-like" black box: tests can state exactly what
should happen. Roles only change two weights. *Cost:* results describe the rule, not language models.

**7. Fault replaces the true entry.** The source holds the false value *instead of* the truth (the fictional capital "changed"),
so it is a full memory corruption, not an added distractor. *Alternative:* add a competing entry. *Cost:* the source cannot
self-correct; only repair or incoming truth can fix it.

**8. Repair as source restoration at a fixed round.** Gives a clean definition of persistence (contamination that outlives its
source) and recovery time. *Cost:* an oracle intervention. `repair_round: null` disables it.

**9. Four topologies, including two decentralised ones.** `dag` (acyclic) and `graph` (cyclic, bidirectional) separate "decentralised"
from "has cycles", which the star and pipeline cannot. *Cost:* the two decentralised generators are only two of many possible ones.

**10. `central` / `peripheral` defined by betweenness.** Peripheral breaks ties by largest reach so that the location is never
trivially harmless (a pipeline's last stage reaches nobody). *Cost:* the labels mean different things across topologies; `random` is available.

**11. Message = digest of a few claims.** `message_facts` claims per used edge, sampled uniformly. This slows contagion of the
single target fact to a realistic fraction of traffic. *Cost:* uniform sampling ignores relevance-driven routing.

**12. Static per-sender trust.** Trust is a scalar per incoming edge; no learning. *Why:* one mechanism at a time.
*Cost:* omits the most obvious defence (learning to distrust a source that contradicts many peers).

**13. Paired no-fault controls and reused seeds.** A control and its fault run share all random structure. Grid cells reuse seed
labels, although draws cannot map one-to-one when graph shape or size changes. *Why:* exact pairing makes `clean_acc_delta` a clean
same-seed difference. *Cost:* cells within a seed are not independent; summaries therefore resample seed-level means, not pooled runs.

**14. Simple bag-of-words retrieval; no embeddings, no torch.** Retrieval quality is not the studied variable, and the core
install stays five small dependencies. *Cost:* retrieval failure modes of vector stores are absent. `torch`/`transformers` are only
an optional extra for the HuggingFace backend.

**15. Standard-library API backend.** OpenAI-compatible chat completions via `urllib`, configured through three environment
variables. No SDK dependency, no key on disk.

**16. Seed-clustered bootstrap intervals, no significance tests in the quick run.** Repeated cells are averaged within a seed
before resampling. With only five seeds these intervals are unstable and descriptive; confirmatory criteria require more seeds.

**17. Results committed only for the quick run.** Small, reproducible, and reviewable. Large grids are regenerated locally and git-ignored.

**18. Undefined metrics stay `NaN`.** `mean_first_passage`, `t_saturation` and `recovery_time` are not filled with zeros; the
summary reports how many runs contributed (`*_n` columns).
