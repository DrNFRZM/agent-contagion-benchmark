"""Communication topologies, source selection, and simple network measures.

Edges are directed: (u, v) means "u may send a message to v".

  star      hub 0 <-> every other agent (centralised orchestration; workers never talk directly)
  pipeline  0 -> 1 -> ... -> n-1 (fixed sequential hand-off, acyclic, strictly one-way)
  dag       node i receives from `dag_in_degree` random earlier nodes (decentralised, acyclic)
  graph     connected Watts-Strogatz small world, every edge bidirectional (decentralised, cyclic)
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

TOPOLOGIES = ("star", "pipeline", "dag", "graph")
FAULT_LOCATIONS = ("central", "peripheral", "random")


def build_topology(name: str, n: int, rng: np.random.Generator, dag_in_degree: int = 2,
                   ws_k: int = 4, ws_beta: float = 0.2) -> nx.DiGraph:
    if n < 3:
        raise ValueError("need at least 3 agents")
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    if name == "star":
        for i in range(1, n):
            G.add_edge(0, i)
            G.add_edge(i, 0)
    elif name == "pipeline":
        G.add_edges_from((i, i + 1) for i in range(n - 1))
    elif name == "dag":
        for i in range(1, n):
            parents = rng.choice(i, size=min(i, dag_in_degree), replace=False)
            G.add_edges_from((int(p), i) for p in parents)
    elif name == "graph":
        k = min(ws_k, n - 1)
        k -= k % 2  # must be even
        seed = int(rng.integers(2**31 - 1))
        U = nx.connected_watts_strogatz_graph(n, max(k, 2), ws_beta, tries=100, seed=seed)
        for u, v in U.edges:
            G.add_edge(u, v)
            G.add_edge(v, u)
    else:
        raise ValueError(f"unknown topology {name!r}; choose from {TOPOLOGIES}")
    return G


def reach(G: nx.DiGraph, u: int) -> int:
    return len(nx.descendants(G, u))


def pick_source(G: nx.DiGraph, mode: str, rng: np.random.Generator) -> int:
    """Where the single fault is injected.

    central     highest betweenness (ties: larger out-degree, then lower id)
    peripheral  lowest betweenness (ties: larger reach, then lower id), so the
                location is never trivially harmless (a pipeline's last stage reaches nobody)
    random      uniform over agents
    """
    nodes = sorted(G.nodes)
    if mode == "random":
        return int(rng.choice(nodes))
    bc = nx.betweenness_centrality(G)
    if mode == "central":
        return max(nodes, key=lambda v: (bc[v], G.out_degree(v), -v))
    if mode == "peripheral":
        return min(nodes, key=lambda v: (bc[v], -reach(G, v), v))
    raise ValueError(f"unknown fault_location {mode!r}; choose from {FAULT_LOCATIONS}")


def distances_from(G: nx.DiGraph, source: int) -> dict[int, float]:
    d = nx.single_source_shortest_path_length(G, source)
    return {v: float(d[v]) if v in d else math.nan for v in G.nodes}


def node_measures(G: nx.DiGraph, source: int) -> dict[int, dict[str, float]]:
    bc = nx.betweenness_centrality(G)
    dist = distances_from(G, source)
    return {
        v: {
            "in_degree": G.in_degree(v),
            "out_degree": G.out_degree(v),
            "degree": G.in_degree(v) + G.out_degree(v),
            "betweenness": bc[v],
            "dist_from_source": dist[v],
        }
        for v in G.nodes
    }


def network_measures(G: nx.DiGraph, source: int) -> dict[str, float]:
    n = G.number_of_nodes()
    lengths = [d for _, dd in nx.all_pairs_shortest_path_length(G) for v, d in dd.items() if d > 0]
    bc = nx.betweenness_centrality(G)
    return {
        "n_edges": G.number_of_edges(),
        "density": nx.density(G),
        "is_dag": nx.is_directed_acyclic_graph(G),
        "mean_degree": 2 * G.number_of_edges() / n,
        "mean_path_length": float(np.mean(lengths)) if lengths else math.nan,
        "diameter": max(lengths) if lengths else math.nan,
        "src_degree": G.in_degree(source) + G.out_degree(source),
        "src_betweenness": bc[source],
        "src_reach": reach(G, source),
    }
