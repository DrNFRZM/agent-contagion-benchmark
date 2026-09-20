import networkx as nx
import numpy as np
import pytest

from acb.topology import TOPOLOGIES, build_topology, network_measures, pick_source


def rng(s=0):
    return np.random.default_rng(s)


def test_star_edges():
    G = build_topology("star", 6, rng())
    assert G.number_of_edges() == 10
    assert all(G.has_edge(0, i) and G.has_edge(i, 0) for i in range(1, 6))
    assert not G.has_edge(1, 2)


def test_pipeline_is_directed_path():
    G = build_topology("pipeline", 6, rng())
    assert sorted(G.edges) == [(i, i + 1) for i in range(5)]
    assert nx.is_directed_acyclic_graph(G)


@pytest.mark.parametrize("seed", range(5))
def test_dag_is_acyclic_and_connected(seed):
    G = build_topology("dag", 12, rng(seed))
    assert nx.is_directed_acyclic_graph(G)
    assert nx.is_weakly_connected(G)
    assert all(G.in_degree(i) == min(i, 2) for i in range(12))


@pytest.mark.parametrize("seed", range(5))
def test_graph_is_connected_and_bidirectional(seed):
    G = build_topology("graph", 10, rng(seed))
    assert nx.is_strongly_connected(G)
    assert all(G.has_edge(v, u) for u, v in G.edges)
    assert not nx.is_directed_acyclic_graph(G)


def test_topology_generation_is_seeded():
    a, b = build_topology("dag", 10, rng(3)), build_topology("dag", 10, rng(3))
    assert sorted(a.edges) == sorted(b.edges)


def test_unknown_topology():
    with pytest.raises(ValueError):
        build_topology("ring", 6, rng())
    assert set(TOPOLOGIES) == {"star", "pipeline", "dag", "graph"}


def test_pick_source_modes():
    star = build_topology("star", 6, rng())
    assert pick_source(star, "central", rng()) == 0
    assert pick_source(star, "peripheral", rng()) == 1
    pipe = build_topology("pipeline", 7, rng())
    assert pick_source(pipe, "central", rng()) == 3       # middle stage has max betweenness
    assert pick_source(pipe, "peripheral", rng()) == 0    # betweenness-0 node with the largest reach
    assert 0 <= pick_source(pipe, "random", rng(1)) < 7


def test_network_measures_pipeline():
    G = build_topology("pipeline", 5, rng())
    m = network_measures(G, 0)
    assert m["is_dag"] and m["src_reach"] == 4 and m["diameter"] == 4
    assert m["mean_path_length"] == pytest.approx(20 / 10)  # distances 1x4,2x3,3x2,4x1 = 20 over 10 pairs
