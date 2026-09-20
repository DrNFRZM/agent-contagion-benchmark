"""Run configuration (one simulation) and YAML experiment specification (a grid of runs)."""
from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

import yaml

from .facts import ATTRS, ENTITIES
from .memory import POLICIES
from .topology import FAULT_LOCATIONS, TOPOLOGIES


@dataclass(frozen=True)
class RunConfig:
    topology: str = "star"
    n_agents: int = 8
    n_facts: int = 8
    rounds: int = 30
    repair_round: int | None = 10   # source's injected entry is restored at the start of this round
    message_facts: int = 2          # claims carried by one message
    comm_prob: float = 0.7          # probability that a chosen edge is used in a round
    fanout: int | None = None       # None: all out-neighbours; k: k random out-neighbours per round
    peer_trust: float = 0.7
    hub_trust: float | None = None  # trust in messages from the star hub (None: same as peer_trust)
    base_conf: float = 0.6          # confidence of seeded true memories
    injected_conf: float = 1.0      # confidence of the injected false memory
    coverage: float = 0.6           # prob. an agent is seeded with a given clean fact
    roles: str = "homogeneous"      # homogeneous | heterogeneous
    retention: str = "keep_all"
    ttl: int = 5
    capacity: int | None = None     # for `bounded`; None -> n_facts
    fault_location: str = "central"
    dag_in_degree: int = 2
    ws_k: int = 4
    ws_beta: float = 0.2
    retrieval_k: int = 4
    backend: str = "mock"

    def __post_init__(self) -> None:
        if self.n_agents < 3:
            raise ValueError("n_agents must be >= 3")
        if not 2 <= self.n_facts <= len(ENTITIES) * len(ATTRS):
            raise ValueError(f"n_facts must be in [2, {len(ENTITIES) * len(ATTRS)}]")
        if self.rounds < 1:
            raise ValueError("rounds must be >= 1")
        if self.topology not in TOPOLOGIES:
            raise ValueError(f"topology must be one of {TOPOLOGIES}")
        if self.retention not in POLICIES:
            raise ValueError(f"retention must be one of {POLICIES}")
        if self.fault_location not in FAULT_LOCATIONS:
            raise ValueError(f"fault_location must be one of {FAULT_LOCATIONS}")
        if self.roles not in ("homogeneous", "heterogeneous"):
            raise ValueError("roles must be homogeneous or heterogeneous")
        if not 0.0 <= self.comm_prob <= 1.0:
            raise ValueError("comm_prob must be in [0, 1]")
        for name, value in (
            ("peer_trust", self.peer_trust),
            ("base_conf", self.base_conf),
            ("injected_conf", self.injected_conf),
            ("coverage", self.coverage),
            ("ws_beta", self.ws_beta),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.hub_trust is not None and not 0.0 <= self.hub_trust <= 1.0:
            raise ValueError("hub_trust must be in [0, 1] or null")
        if self.repair_round is not None and not 1 <= self.repair_round <= self.rounds:
            raise ValueError("repair_round must be in [1, rounds] or null")
        if not 1 <= self.message_facts <= self.n_facts:
            raise ValueError("message_facts must be in [1, n_facts]")
        if self.fanout is not None and self.fanout < 0:
            raise ValueError("fanout must be >= 0 or null")
        if self.ttl < 0:
            raise ValueError("ttl must be >= 0")
        if self.capacity is not None and self.capacity < 1:
            raise ValueError("capacity must be >= 1 or null")
        if self.dag_in_degree < 1:
            raise ValueError("dag_in_degree must be >= 1")
        if self.ws_k < 2:
            raise ValueError("ws_k must be >= 2")
        if self.retrieval_k < 1:
            raise ValueError("retrieval_k must be >= 1")
        if self.backend not in ("mock", "hf", "api"):
            raise ValueError("backend must be mock, hf or api")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: Any) -> "RunConfig":
        """Rebuild a config from a runs.csv row (pandas turns ints/None into floats/NaN)."""
        ints = {"n_agents", "n_facts", "rounds", "repair_round", "message_facts", "fanout", "ttl", "capacity",
                "dag_in_degree", "ws_k", "retrieval_k"}
        kw: dict[str, Any] = {}
        for f in fields(cls):
            v = row[f.name]
            if v is None or (isinstance(v, float) and v != v):
                kw[f.name] = None
            else:
                kw[f.name] = int(v) if f.name in ints else (v.item() if hasattr(v, "item") else v)
        return cls(**kw)


_FIELDS = {f.name for f in fields(RunConfig)}


@dataclass
class ExperimentSpec:
    name: str
    seeds: list[int]
    base: dict[str, Any]
    grid: dict[str, list[Any]]

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("experiment name must be a non-empty string")
        if not self.seeds or any(not isinstance(s, int) or isinstance(s, bool) for s in self.seeds):
            raise ValueError("seeds must be a non-empty list of integers")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be unique")
        bad = [k for k, values in self.grid.items() if not isinstance(values, list) or not values]
        if bad:
            raise ValueError(f"grid fields must contain non-empty lists: {sorted(bad)}")

    def configs(self) -> list[RunConfig]:
        unknown = (set(self.base) | set(self.grid)) - _FIELDS
        if unknown:
            raise ValueError(f"unknown config fields: {sorted(unknown)}")
        base = RunConfig(**self.base)
        keys = list(self.grid)
        return [replace(base, **dict(zip(keys, vals))) for vals in itertools.product(*self.grid.values())]

    @property
    def varied(self) -> list[str]:
        return [k for k, v in self.grid.items() if len(v) > 1]


def load_spec(path: str | Path) -> ExperimentSpec:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ExperimentSpec(
        name=raw["name"], seeds=list(raw["seeds"]), base=dict(raw.get("base", {})), grid=dict(raw.get("grid", {}))
    )
