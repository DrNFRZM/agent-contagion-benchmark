"""Backend interface and the prompt format shared by all backends.

A backend is anything with `generate(system, prompt) -> str`. The prompt format
is deliberately rigid so that (a) the deterministic mock can parse it and (b)
real models get an unambiguous question. Agents never see backend internals.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

ROLES = {
    "worker": "You answer from your notes and weigh new information from colleagues normally.",
    "orchestrator": "You coordinate the other agents and weigh information from colleagues normally.",
    "verifier": (
        "You double-check claims. You prefer your own stored notes over a single "
        "colleague's claim unless several sources agree."
    ),
    "relay": "You tend to accept fresh information from colleagues over your own older notes.",
}


class LLMBackend(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        """Return the model's text reply. Must be deterministic for the mock."""


def build_system(agent_name: str, role: str) -> str:
    return (
        f"You are agent {agent_name} in a small team that keeps notes about fictional planets. "
        f"ROLE: {role}. {ROLES[role]}"
    )


def build_prompt(question: str, memory: list[tuple[float, str]], messages: list[tuple[float, str]]) -> str:
    lines = [f"QUESTION: {question}", "MEMORY:"]
    lines += [f"- conf={c:.2f} :: {t}" for c, t in memory] or ["- (empty)"]
    lines.append("MESSAGES:")
    lines += [f"- weight={w:.2f} :: {t}" for w, t in messages] or ["- (none)"]
    lines.append(
        "Answer with the single value only. Use the notes weighted by conf/weight. "
        "If nothing supports an answer, reply UNKNOWN."
    )
    return "\n".join(lines)


def parse_answer(text: str, candidates: list[str]) -> str | None:
    """Map free text to one of the candidate values (earliest mention wins), else None."""
    best: tuple[int, str] | None = None
    for c in candidates:
        m = re.search(rf"\b{re.escape(c)}\b", text, flags=re.IGNORECASE)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), c)
    return best[1] if best else None
