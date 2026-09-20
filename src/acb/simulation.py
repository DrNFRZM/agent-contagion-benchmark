"""Synchronous-round simulation of one fault in one multi-agent network.

Round t = 1..T
  1. (optional) repair: at `repair_round` the source agent's injected entry is replaced by the truth.
  2. send:    every out-edge of every agent is used with probability p; an active edge
              carries `message_facts` claims, each the sender's belief (from the previous
              probe) with its memory confidence. Senders that do not know a fact send nothing for it.
  3. absorb:  each receiver reconciles its memory with its inbox via one LLM call per fact.
  4. retain:  the retention policy expires / evicts items.
  5. probe:   every agent answers every fact from memory only. An agent is "contaminated"
              iff it answers the false value for the target fact.

Random draws (edge use, claim selection, topology, coverage, roles) never depend on
belief content, so a fault run and its control run with the same seed share all random
structure: they differ only through the injected fault.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .agent import Agent, Belief, Message
from .config import RunConfig
from .facts import TARGET_FALSE_VALUE, Fact, build_world, target_fact
from .llm import LLMBackend, make_backend
from .memory import Memory
from .topology import build_topology, distances_from, network_measures, node_measures, pick_source

_HETERO_MIX = ["worker", "worker", "verifier", "relay"]  # repeated to length n, then shuffled


class _CountingLLM(LLMBackend):
    def __init__(self, inner: LLMBackend) -> None:
        self.inner, self.calls, self.name = inner, 0, inner.name

    def generate(self, system: str, prompt: str) -> str:
        self.calls += 1
        return self.inner.generate(system, prompt)


@dataclass
class RunResult:
    cfg: RunConfig
    seed: int
    fault: bool
    source: int | None
    series: list[dict]                 # one row per t = 0..T
    first_infected: dict[int, int]     # agent -> first round contaminated (source: 0)
    hops: dict[int, int | None]        # agent -> infection-tree depth (None: no false message received)
    dist: dict[int, float]             # graph distance from the source
    node_stats: dict[int, dict]
    net: dict
    roles: dict[int, str]
    edges: list[tuple[int, int]] = field(default_factory=list)
    llm_calls: int = 0


def _rngs(seed: int) -> dict[str, np.random.Generator]:
    return {k: np.random.default_rng([seed, i]) for i, k in enumerate(["topo", "comm", "setup", "src"])}


def simulate(cfg: RunConfig, seed: int, fault: bool = True, backend: LLMBackend | None = None) -> RunResult:
    rng = _rngs(seed)
    llm = _CountingLLM(backend or make_backend(cfg.backend))
    world = build_world(cfg.n_facts)
    target = target_fact(world)
    by_fid: dict[str, Fact] = {f.fid: f for f in world}
    n = cfg.n_agents

    G = build_topology(cfg.topology, n, rng["topo"], cfg.dag_in_degree, cfg.ws_k, cfg.ws_beta)
    source = pick_source(G, cfg.fault_location, rng["src"])

    # roles
    if cfg.roles == "heterogeneous":
        pool = (_HETERO_MIX * n)[:n]
        roles = [str(r) for r in rng["setup"].permutation(pool)]
    else:
        roles = ["worker"] * n
    if cfg.topology == "star":
        roles[0] = "orchestrator"

    # seeded knowledge: everyone knows the target; each clean fact known w.p. `coverage`, by >= 1 agent
    known = rng["setup"].random((n, len(world))) < cfg.coverage
    known[:, 0] = True
    for j in range(1, len(world)):
        if not known[:, j].any():
            known[int(rng["setup"].integers(n)), j] = True

    capacity = cfg.capacity or cfg.n_facts
    agents: list[Agent] = []
    for i in range(n):
        mem = Memory(cfg.retention, cfg.ttl, capacity)
        for j, f in enumerate(world):
            if known[i, j]:
                mem.write(f.fid, f.value, f.statement(), cfg.base_conf, "base", 0)
        trust = {u: cfg.peer_trust for u in G.predecessors(i)}
        if cfg.topology == "star" and i != 0 and cfg.hub_trust is not None:
            trust[0] = cfg.hub_trust
        agents.append(Agent(i, roles[i], mem, llm, trust, cfg.peer_trust, cfg.retrieval_k))

    if fault:
        m = agents[source].memory
        m.remove(target.fid, target.value)
        m.write(target.fid, TARGET_FALSE_VALUE, target.statement(TARGET_FALSE_VALUE), cfg.injected_conf, "injected", 0)

    clean = [f for f in world if f.fid != target.fid]

    def probe() -> list[dict[str, Belief]]:
        return [{f.fid: a.believe(f) for f in world} for a in agents]

    def contaminated(bel: list[dict[str, Belief]]) -> set[int]:
        return {i for i, b in enumerate(bel) if b[target.fid].value == TARGET_FALSE_VALUE}

    def row(t: int, bel, msgs: int, false_msgs: int, active: int) -> dict:
        c = contaminated(bel)
        acc = np.mean([bel[i][f.fid].value == f.value for i in range(n) for f in clean])
        return {
            "t": t, "n_contaminated": len(c), "prevalence": len(c) / n,
            "clean_acc": float(acc),
            "target_true_frac": float(np.mean([bel[i][target.fid].value == target.value for i in range(n)])),
            "messages": msgs, "false_claims": false_msgs, "active_edges": active,
            "mean_memory_items": float(np.mean([len(a.memory) for a in agents])),
        }

    beliefs = probe()
    series = [row(0, beliefs, 0, 0, 0)]
    first: dict[int, int] = {}
    hops: dict[int, int | None] = {}
    if fault:
        first[source], hops[source] = 0, 0
    seen = contaminated(beliefs)
    for v in seen - set(first):  # (only the source, unless the seed state is already odd)
        first[v], hops[v] = 0, None

    for t in range(1, cfg.rounds + 1):
        if fault and cfg.repair_round == t:
            m = agents[source].memory
            m.remove(target.fid, TARGET_FALSE_VALUE)
            m.write(target.fid, target.value, target.statement(), cfg.base_conf, "base", t)

        inbox: dict[int, list[Message]] = {i: [] for i in range(n)}
        active = 0
        for u in range(n):
            nbrs = sorted(G.successors(u))
            if not nbrs:
                continue
            if cfg.fanout is not None and cfg.fanout < len(nbrs):
                nbrs = sorted(int(x) for x in rng["comm"].choice(nbrs, size=cfg.fanout, replace=False))
            draws = rng["comm"].random(len(nbrs))
            for v, d in zip(nbrs, draws):
                keys = rng["comm"].choice(len(world), size=min(cfg.message_facts, len(world)), replace=False)
                if d >= cfg.comm_prob:
                    continue
                active += 1
                for k in sorted(int(x) for x in keys):
                    fid = world[k].fid
                    b = beliefs[u][fid]
                    if b.value is not None:
                        inbox[v].append(Message(t, u, v, fid, b.value, b.conf))

        msgs = sum(len(x) for x in inbox.values())
        false_msgs = sum(1 for x in inbox.values() for m in x if m.fid == target.fid and m.value == TARGET_FALSE_VALUE)
        for v in range(n):
            groups: dict[str, list[Message]] = {}
            for m in inbox[v]:
                groups.setdefault(m.fid, []).append(m)
            for fid in sorted(groups):
                agents[v].absorb(by_fid[fid], groups[fid], t)
            agents[v].memory.end_of_round(t)

        beliefs = probe()
        now = contaminated(beliefs)
        for v in sorted(now - seen):
            if v in first:
                continue
            first[v] = t
            senders = [m.sender for m in inbox[v] if m.fid == target.fid and m.value == TARGET_FALSE_VALUE
                       and hops.get(m.sender) is not None]
            hops[v] = 1 + min(hops[s] for s in senders) if senders else None
        seen |= now
        series.append(row(t, beliefs, msgs, false_msgs, active))

    return RunResult(
        cfg=cfg, seed=seed, fault=fault, source=source if fault else None, series=series,
        first_infected=first, hops=hops, dist=distances_from(G, source), node_stats=node_measures(G, source),
        net=network_measures(G, source), roles=dict(enumerate(roles)), edges=sorted(G.edges), llm_calls=llm.calls,
    )

