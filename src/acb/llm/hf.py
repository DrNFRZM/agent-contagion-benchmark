"""Optional local HuggingFace backend (greedy decoding).

Requires `pip install -e .[hf]` (torch + transformers). The model is chosen with
ACB_HF_MODEL (default: a small instruction-tuned model). Weights are downloaded by
transformers into its own cache, outside this repository. Tests use offline fakes;
CI never downloads or executes model weights.
"""
from __future__ import annotations

import os

from .base import LLMBackend


class HFBackend(LLMBackend):
    name = "hf"

    def __init__(self, model: str | None = None, max_new_tokens: int = 12) -> None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415
        except ImportError as e:  # pragma: no cover - optional dependency
            raise RuntimeError("HF backend needs `pip install -e .[hf]`") from e
        self.model_name = model or os.environ.get("ACB_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        self.max_new_tokens = max_new_tokens
        self.tok = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self.model.eval()

    def generate(self, system: str, prompt: str) -> str:  # pragma: no cover - needs weights
        import torch  # noqa: PLC0415

        msgs = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        ids = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
        with torch.no_grad():
            out = self.model.generate(ids, max_new_tokens=self.max_new_tokens, do_sample=False)
        return self.tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()
