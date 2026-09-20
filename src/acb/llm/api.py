"""Optional OpenAI-compatible chat-completions backend, configured by environment.

  ACB_API_BASE   e.g. https://api.example.com/v1   (required)
  ACB_API_KEY    bearer token                       (required; never written to disk by this repo)
  ACB_API_MODEL  model name                         (required)

Uses only the standard library. Tests replace the network call with an offline fake;
CI never contacts an endpoint.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .base import LLMBackend


class APIBackend(LLMBackend):
    name = "api"

    def __init__(self, timeout: float = 60.0) -> None:
        missing = [k for k in ("ACB_API_BASE", "ACB_API_KEY", "ACB_API_MODEL") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"API backend needs environment variables: {', '.join(missing)}")
        self.base = os.environ["ACB_API_BASE"].rstrip("/")
        self._key = os.environ["ACB_API_KEY"]
        self.model = os.environ["ACB_API_MODEL"]
        self.timeout = timeout

    def generate(self, system: str, prompt: str) -> str:
        body = json.dumps({
            "model": self.model,
            "temperature": 0,
            "max_tokens": 16,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/chat/completions", data=body, method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - user-configured endpoint
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
