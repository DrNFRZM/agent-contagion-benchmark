"""An agent: identity, role, local memory, message history, per-sender trust.

All belief formation goes through the LLM backend. The agent's own code only does
bookkeeping: build the prompt from retrieved memory (+ incoming messages), parse
the reply, and write accepted evidence into memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .facts import Fact
from .llm import LLMBackend, build_prompt, build_system, parse_answer
from .memory import Memory


@dataclass(frozen=True)
class Message:
    rnd: int
    sender: int
    receiver: int
    fid: str
    value: str
    conf: float  # sender's confidence in the claim (before receiver-side trust)


@dataclass(frozen=True)
class Belief:
    value: str | None  # None = UNKNOWN
    conf: float = 0.0


@dataclass
class Agent:
    aid: int
    role: str
    memory: Memory
    llm: LLMBackend
    trust: dict[int, float] = field(default_factory=dict)  # sender id -> trust in [0, 1]
    default_trust: float = 0.7
    retrieval_k: int = 4
    history: list[Message] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"A{self.aid}"

    def _ask(self, fact: Fact, msgs: list[Message]) -> str | None:
        items = self.memory.retrieve(fact.question, self.retrieval_k)
        mem_lines = [(it.conf, it.text) for it in items]
        msg_lines = [(m.conf * self.trust.get(m.sender, self.default_trust), fact.statement(m.value)) for m in msgs]
        prompt = build_prompt(fact.question, mem_lines, msg_lines)
        reply = self.llm.generate(build_system(self.name, self.role), prompt)
        candidates = [it.value for it in items if it.fid == fact.fid] + [m.value for m in msgs]
        return parse_answer(reply, candidates)

    def believe(self, fact: Fact) -> Belief:
        """Answer from memory only (used as the per-round probe and as message content)."""
        ans = self._ask(fact, [])
        return Belief(ans, self.memory.support(fact.fid, ans) if ans else 0.0)

    def absorb(self, fact: Fact, msgs: list[Message], rnd: int) -> None:
        """Reconcile memory with this round's messages about one fact."""
        self.history.extend(msgs)
        ans = self._ask(fact, msgs)
        if ans is None:
            return
        for m in msgs:
            if m.value == ans:  # accepted evidence is stored / reinforced; rejected is dropped
                w = m.conf * self.trust.get(m.sender, self.default_trust)
                self.memory.write(fact.fid, ans, fact.statement(ans), w, "learned", rnd)
        self.memory.resolve(fact.fid, ans)
