"""Agent-local memory: items with confidence, bag-of-words retrieval, retention policies.

An item is one (fact id, value) pair with a confidence in (0, 1). Two agents
(or two messages) supporting the same (fact, value) are merged into one item
whose confidence is combined with a noisy-OR, so repeated agreement raises
confidence but never past CONF_CAP.

Retention policies decide what is kept after an update:

  keep_all   every item stays (conflicting values coexist as competing evidence)
  overwrite  when a value wins for a fact, all rival items for that fact are deleted
  ttl        items learned from messages expire `ttl` rounds after last reinforcement;
             base (seed) items never expire, the injected item never expires
  bounded    at most `capacity` items; lowest-confidence, oldest items are evicted
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CONF_CAP = 0.99
POLICIES = ("keep_all", "overwrite", "ttl", "bounded")
_STOP = {"what", "is", "the", "of", "a", "an"}
_WORD = re.compile(r"[a-z]+")


def tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


def noisy_or(a: float, b: float) -> float:
    return min(CONF_CAP, 1.0 - (1.0 - a) * (1.0 - b))


@dataclass
class MemoryItem:
    fid: str
    value: str
    text: str
    conf: float
    source: str          # "base" | "injected" | "learned"
    born: int
    last_seen: int

    def key(self) -> tuple[str, str]:
        return (self.fid, self.value)


@dataclass
class Memory:
    policy: str = "keep_all"
    ttl: int = 5
    capacity: int = 8
    items: list[MemoryItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.policy not in POLICIES:
            raise ValueError(f"unknown retention policy {self.policy!r}; choose from {POLICIES}")

    # --- writing -----------------------------------------------------------
    def find(self, fid: str, value: str) -> MemoryItem | None:
        for it in self.items:
            if it.fid == fid and it.value == value:
                return it
        return None

    def write(self, fid: str, value: str, text: str, conf: float, source: str, rnd: int) -> None:
        """Insert a new item or reinforce the existing one (noisy-OR)."""
        it = self.find(fid, value)
        if it is None:
            self.items.append(MemoryItem(fid, value, text, min(conf, CONF_CAP), source, rnd, rnd))
        else:
            it.conf = noisy_or(it.conf, conf)
            it.last_seen = rnd
            # An oracle repair or explicit injection must not remain tagged as a
            # transient learned item merely because the same value was heard first.
            # Learned reinforcement never downgrades a persistent base/injected item.
            if source != "learned":
                it.source = source

    def remove(self, fid: str, value: str) -> None:
        self.items = [it for it in self.items if not (it.fid == fid and it.value == value)]

    def resolve(self, fid: str, winner: str) -> None:
        """Apply the overwrite policy after `winner` won for `fid`."""
        if self.policy == "overwrite":
            self.items = [it for it in self.items if it.fid != fid or it.value == winner]

    def end_of_round(self, rnd: int) -> None:
        """Expire / evict according to the policy. Called once per round."""
        if self.policy == "ttl":
            self.items = [
                it for it in self.items
                if it.source != "learned" or rnd - it.last_seen <= self.ttl
            ]
        elif self.policy == "bounded" and len(self.items) > self.capacity:
            # evict lowest confidence first, oldest first among ties
            order = sorted(self.items, key=lambda it: (it.conf, it.last_seen))
            drop = {id(it) for it in order[: len(self.items) - self.capacity]}
            self.items = [it for it in self.items if id(it) not in drop]

    # --- reading -----------------------------------------------------------
    def retrieve(self, query: str, k: int = 4) -> list[MemoryItem]:
        """Top-k items by query-token overlap, then confidence, then insertion order."""
        q = tokens(query)
        if not q:
            return []
        scored = []
        for idx, it in enumerate(self.items):
            s = len(q & tokens(it.text)) / len(q)
            if s > 0:
                scored.append((-s, -it.conf, idx, it))
        scored.sort(key=lambda t: t[:3])
        return [t[3] for t in scored[:k]]

    def support(self, fid: str, value: str) -> float:
        it = self.find(fid, value)
        return it.conf if it else 0.0

    def __len__(self) -> int:
        return len(self.items)
