"""Synthetic world: harmless fictional facts about invented planets.

Every fact has the form "The <attr> of <Entity> is <Value>." Nothing here refers
to the real world. The injected false value for the target fact is another
invented word, so a "contaminated" agent is simply one that answers
"Mira" instead of "Arden" when asked for the capital of the planet Veloria.
"""
from __future__ import annotations

from dataclasses import dataclass

ENTITIES = ["Veloria", "Tarnis", "Ostrel", "Quorin", "Zyphra", "Norvane", "Lumeth", "Kaldor"]
ATTRS = ["capital", "river", "moon"]

# One invented value per (entity, attr) pair, entity-major order. All unique.
_VALUES = [
    "Arden", "Selu", "Ombra",       # Veloria
    "Kestrin", "Vaal", "Pyx",       # Tarnis
    "Dovan", "Rhee", "Tolu",        # Ostrel
    "Halvir", "Nesk", "Ilo",        # Quorin
    "Brenna", "Yuma", "Cael",       # Zyphra
    "Ostren", "Fael", "Dru",        # Norvane
    "Mavro", "Sinn", "Eko",         # Lumeth
    "Tavik", "Woru", "Lyra",        # Kaldor
]

TARGET_FALSE_VALUE = "Mira"  # the injected false capital of Veloria


@dataclass(frozen=True)
class Fact:
    entity: str
    attr: str
    value: str  # ground truth

    @property
    def fid(self) -> str:
        return f"{self.entity}.{self.attr}"

    def statement(self, value: str | None = None) -> str:
        return f"The {self.attr} of {self.entity} is {value or self.value}."

    @property
    def question(self) -> str:
        return f"What is the {self.attr} of {self.entity}?"


def build_world(n_facts: int) -> list[Fact]:
    """First `n_facts` facts. Fact 0 (capital of Veloria) is always the target."""
    max_facts = len(ENTITIES) * len(ATTRS)
    if not 2 <= n_facts <= max_facts:
        raise ValueError(f"n_facts must be in [2, {max_facts}]")
    facts = []
    for i in range(n_facts):
        facts.append(Fact(ENTITIES[i // len(ATTRS)], ATTRS[i % len(ATTRS)], _VALUES[i]))
    return facts


def target_fact(world: list[Fact]) -> Fact:
    return world[0]
