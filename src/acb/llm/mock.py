"""Deterministic mock backend: a transparent evidence-weighting rule, no network.

For the asked (attribute, entity) it adds up, per candidate value,
    w_mem * sum(conf of matching MEMORY lines) + w_msg * sum(weight of matching MESSAGES lines)
and answers the value with the largest total (ties -> value listed first, i.e. the
older MEMORY line wins). It replies UNKNOWN if no line matches. The role in the
system prompt only changes (w_mem, w_msg). This is a stand-in for "an LLM that
reconciles notes by weight"; it is not a claim about how real LLMs behave.
"""
from __future__ import annotations

import re

from .base import LLMBackend

# role -> (memory weight, message weight)
ROLE_WEIGHTS = {
    "worker": (1.0, 1.0),
    "orchestrator": (1.0, 1.0),
    "verifier": (1.5, 0.75),
    "relay": (0.75, 1.25),
}
_Q = re.compile(r"QUESTION: What is the (?P<attr>[a-z ]+) of (?P<ent>[A-Z][a-z]+)\?")
_LINE = re.compile(
    r"^- (?P<kind>conf|weight)=(?P<x>[0-9.]+) :: The (?P<attr>[a-z ]+) of (?P<ent>[A-Z][a-z]+) is (?P<val>[A-Z][a-z]+)\.$"
)
_ROLE = re.compile(r"ROLE: (\w+)\.")


class DeterministicMockLLM(LLMBackend):
    name = "mock"

    def generate(self, system: str, prompt: str) -> str:
        rm = _ROLE.search(system)
        w_mem, w_msg = ROLE_WEIGHTS.get(rm[1] if rm else "worker", (1.0, 1.0))
        q = _Q.search(prompt)
        if not q:
            return "UNKNOWN"
        scores: dict[str, float] = {}
        for line in prompt.splitlines():
            m = _LINE.match(line)
            if not m or m["attr"] != q["attr"] or m["ent"] != q["ent"]:
                continue
            w = w_mem if m["kind"] == "conf" else w_msg
            scores[m["val"]] = scores.get(m["val"], 0.0) + w * float(m["x"])
        if not scores:
            return "UNKNOWN"
        best = max(scores.values())
        return next(v for v, s in scores.items() if s == best)  # dict keeps first-seen order
