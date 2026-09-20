from .base import LLMBackend, build_prompt, build_system, parse_answer
from .mock import DeterministicMockLLM


def make_backend(name: str = "mock") -> LLMBackend:
    """Factory. hf/api are imported lazily so the core install stays dependency-light."""
    if name == "mock":
        return DeterministicMockLLM()
    if name == "hf":
        from .hf import HFBackend

        return HFBackend()
    if name == "api":
        from .api import APIBackend

        return APIBackend()
    raise ValueError(f"unknown backend {name!r}; choose mock, hf or api")


__all__ = ["LLMBackend", "DeterministicMockLLM", "make_backend", "build_prompt", "build_system", "parse_answer"]
