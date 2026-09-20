import math
from types import SimpleNamespace

import pytest

from acb.config import RunConfig
from acb.metrics import compute_metrics
from acb.simulation import simulate


def cfg(**kw):
    return RunConfig(**{"n_agents": 8, "rounds": 20, "repair_round": 8, **kw})


def test_exactly_one_contaminated_at_t0_and_control_clean():
    for topo in ("star", "pipeline", "dag", "graph"):
        r = simulate(cfg(topology=topo), 0)
        assert r.series[0]["n_contaminated"] == 1
        c = simulate(cfg(topology=topo), 0, fault=False)
        assert max(x["n_contaminated"] for x in c.series) == 0


def test_no_communication_means_no_spread():
    r = simulate(cfg(topology="star", comm_prob=0.0), 1)
    assert all(x["n_contaminated"] <= 1 for x in r.series) and r.series[-1]["messages"] == 0
    assert r.series[-1]["n_contaminated"] == 0  # repaired source, nobody else affected


def test_deterministic_given_seed():
    a, b = simulate(cfg(topology="graph"), 4), simulate(cfg(topology="graph"), 4)
    assert a.series == b.series and a.first_infected == b.first_infected
    assert simulate(cfg(topology="graph"), 5).series != a.series


def test_pipeline_contamination_only_downstream():
    for seed in range(5):
        r = simulate(cfg(topology="pipeline", fault_location="central"), seed)
        assert set(r.first_infected) <= {3, 4, 5, 6, 7}   # source 3 and its descendants
        assert r.hops[3] == 0


def test_hops_and_first_passage_consistent_with_distance():
    for seed in range(5):
        r = simulate(cfg(topology="dag"), seed)
        for v, t in r.first_infected.items():
            if v == r.source:
                continue
            assert t >= 1
            assert r.hops[v] is None or r.hops[v] >= r.dist[v]  # infection path >= shortest path


def test_fault_and_control_share_random_structure():
    r, c = simulate(cfg(topology="graph"), 2), simulate(cfg(topology="graph"), 2, fault=False)
    assert r.edges == c.edges
    assert [x["active_edges"] for x in r.series] == [x["active_edges"] for x in c.series]


def test_star_hub_fault_spreads_more_than_leaf_fault():
    def radius(loc):
        return sum(compute_metrics(simulate(cfg(topology="star", fault_location=loc), s))["contagion_radius"]
                   for s in range(10))
    assert radius("central") > radius("peripheral")


def test_mock_backend_only_default():
    assert RunConfig().backend == "mock"


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        RunConfig(topology="mesh")
    with pytest.raises(ValueError):
        RunConfig(comm_prob=1.5)
    with pytest.raises(ValueError):
        RunConfig(repair_round=99, rounds=10)
    with pytest.raises(ValueError):
        RunConfig(n_agents=2)
    with pytest.raises(ValueError):
        RunConfig(coverage=-0.1)
    with pytest.raises(ValueError):
        RunConfig(message_facts=9, n_facts=8)
    with pytest.raises(ValueError):
        RunConfig(backend="unknown")


# ---- metrics on a hand-built result -----------------------------------------
def fake_result(n_t, first, hops, dist, repair=3, n=5, source=0):
    series = [{"n_contaminated": k, "clean_acc": 1.0, "messages": 2, "false_claims": 1} for k in n_t]
    return SimpleNamespace(cfg=SimpleNamespace(n_agents=n, repair_round=repair), source=source, series=series,
                           first_infected=first, hops=hops, dist=dist, llm_calls=0)


def test_metrics_by_hand():
    # source 0; agent 1 infected at t=1 (1 hop), agent 2 at t=2 (2 hops); repair at t=3; clean at t=5
    res = fake_result([1, 2, 3, 3, 2, 0, 0], {0: 0, 1: 1, 2: 2}, {0: 0, 1: 1, 2: 2}, {0: 0, 1: 1, 2: 2, 3: 3, 4: math.nan})
    m = compute_metrics(res)
    assert m["contagion_radius"] == pytest.approx(2 / 4)
    assert m["peak_prevalence"] == pytest.approx(3 / 5) and m["t_peak"] == 2
    assert m["t_saturation"] == 2            # first t with n_t >= 0.9 * 3
    assert m["mean_first_passage"] == pytest.approx(1.5) and m["t_first_spread"] == 1
    assert m["max_hops"] == 2 and m["max_graph_distance"] == 2
    assert m["persistence_rounds"] == 2      # t=3 and t=4 have contamination after repair round 3
    assert m["recovered"] and m["recovery_time"] == 2 and not m["persisted"]


def test_metrics_no_spread_and_persistent():
    res = fake_result([1, 1, 1, 1], {0: 0}, {0: 0}, {0: 0}, repair=None)
    m = compute_metrics(res)
    assert m["contagion_radius"] == 0 and math.isnan(m["t_saturation"]) and math.isnan(m["mean_first_passage"])
    assert m["persisted"] and not m["recovered"] and math.isnan(m["recovery_time"])
    assert m["max_hops"] == 0
