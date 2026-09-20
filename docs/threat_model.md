# Threat model

This document fixes what the benchmark assumes and what it does and does not test. It is a **fault model for a
closed simulation**, not a threat model for a deployed product.

## 1. Assets

| Asset | Why it matters | How the benchmark observes it |
|---|---|---|
| **Integrity of each agent's memory** for a given fact | Downstream answers and messages are computed from it | The agent's memory-only answer to a fixed question |
| **Correctness of the system's collective answer** to the target question | This is what a user of the multi-agent system would consume | Fraction of agents answering the true / false value |
| **Correctness of unrelated ("clean") answers** | A local fault should not degrade other knowledge | Clean-task accuracy vs a paired no-fault control |
| **Recoverability** | A fault that survives repair of its source is systemic | Persistence and recovery time after the source is restored |
| **Message-channel integrity** | Agents treat colleagues' messages as evidence | Not attacked: messages are delivered faithfully |

## 2. Trust assumptions

- The topology is fixed and known; edges are honest channels (no spoofing, no dropped-message attacks other than random non-use).
- Every agent is *honest but fallible*: it reports what it believes, with its own confidence. Nobody lies deliberately after injection.
- Trust in a sender is a static scalar (`peer_trust`, optionally `hub_trust` for the star hub); it is not learned or revised.
- The orchestrator in `star` is an ordinary agent that relays what it believes. It has no special verification ability.
- The ground truth is known to the experimenter only; agents cannot consult it.
- The repair event is an oracle: at a chosen round the experimenter restores the true entry at the source. It models "someone found and fixed the bad record".

## 3. Fault / adversary model

- **One fault, injected once, at t = 0**: exactly one agent's memory entry for one fact is replaced by a false value with high
  confidence (`injected_conf`, default 1.0). Example: capital of *Veloria* "Arden" → "Mira".
- **Where**: `central` (highest betweenness), `peripheral` (lowest betweenness, then largest reach), or `random`.
- **Non-adaptive**: after injection the faulty agent behaves like every other agent. No re-injection, no targeting of
  messages, no learning about the topology.
- **Content-neutral**: the false value is a plain word. The fault contains no instructions and is not designed to persuade.
- **Capability**: write access to one memory item of one agent. Nothing else.

### Accidental vs adversarial (why the model is neutral between them)

The same injected entry could come from an accident (a hallucination written to memory, a stale record, a corrupted tool output)
or from an adversary (memory poisoning). At the level of this benchmark they are **indistinguishable**: one false, confident
memory entry. What differs in reality, and is *not* modelled here: an adversary may choose the location, timing, wording and
persuasiveness of the payload, re-inject it, adapt to defences, or target a high-leverage node. The results characterise only
the accidental / non-adaptive fault model; they are not a quantitative bound on an adaptive attack.

## 4. What is being tested

- How a single false belief spreads through a **fixed** communication structure (radius, timing, hops).
- How it interacts with memory retention (keep, overwrite, expire, bounded).
- Whether it outlives the repair of its source (persistence) and how long recovery takes.
- Whether clean answers are affected (spillover), given a paired control.
- Sensitivity to location, network size, communication probability, and role heterogeneity.

## 5. What is not being tested

- Real-world LLM behaviour under the mock backend (only optional, unvalidated backends touch real models).
- Prompt injection, jailbreaks, tool abuse, code execution, data exfiltration, authentication, or network security.
- Adaptive or colluding adversaries, Sybil agents, or Byzantine behaviour.
- Defences such as cross-verification, quorum, provenance tracking, or trust learning (these are natural extensions).
- Real deployments, real memory stores (vector databases), or real retrieval quality.

## 6. Safety boundary

All facts are fictional and harmless. The project contains no exploit code, no external targets, no credentials handling beyond
an optional user-supplied API key read from the environment, and no destructive payloads. See [../SECURITY.md](../SECURITY.md).
