import json
import sys
import types
from contextlib import contextmanager

import numpy as np

import pytest

from acb.facts import TARGET_FALSE_VALUE, build_world
from acb.llm import DeterministicMockLLM, build_prompt, build_system, make_backend, parse_answer
from acb.llm.base import ROLES
from acb.memory import CONF_CAP, Memory, noisy_or

W = build_world(8)
T = W[0]  # capital of Veloria


def test_world_is_synthetic_and_unique():
    assert T.statement() == "The capital of Veloria is Arden."
    assert len({f.fid for f in W}) == 8
    assert TARGET_FALSE_VALUE not in {f.value for f in build_world(24)}


def test_noisy_or_monotone_and_capped():
    assert noisy_or(0.5, 0.5) == pytest.approx(0.75)
    assert noisy_or(0.98, 0.98) == CONF_CAP


def test_retrieval_puts_same_fact_items_first():
    m = Memory()
    for f in W:
        m.write(f.fid, f.value, f.statement(), 0.6, "base", 0)
    m.write(T.fid, "Mira", T.statement("Mira"), 0.7, "learned", 1)
    top = m.retrieve(T.question, k=4)
    assert {it.value for it in top[:2]} == {"Arden", "Mira"}
    assert all(it.fid == T.fid for it in top[:2])


def test_write_merges_same_value():
    m = Memory()
    m.write(T.fid, "Arden", T.statement(), 0.6, "base", 0)
    m.write(T.fid, "Arden", T.statement(), 0.5, "learned", 3)
    assert len(m) == 1 and m.items[0].conf == pytest.approx(0.8) and m.items[0].source == "base"


def test_repair_promotes_a_learned_item_to_persistent_base():
    m = Memory("ttl", ttl=1)
    m.write(T.fid, "Arden", T.statement(), 0.5, "learned", 2)
    m.write(T.fid, "Arden", T.statement(), 0.6, "base", 3)
    m.end_of_round(10)
    assert len(m) == 1 and m.items[0].source == "base"


def test_overwrite_deletes_rivals():
    m = Memory("overwrite")
    m.write(T.fid, "Arden", T.statement(), 0.6, "base", 0)
    m.write(T.fid, "Mira", T.statement("Mira"), 0.7, "learned", 1)
    m.resolve(T.fid, "Mira")
    assert [it.value for it in m.items] == ["Mira"]


def test_ttl_expires_learned_but_not_base_or_injected():
    m = Memory("ttl", ttl=3)
    m.write(T.fid, "Arden", T.statement(), 0.6, "base", 0)
    m.write(T.fid, "Mira", T.statement("Mira"), 0.7, "learned", 1)
    m.write(W[1].fid, "Zed", W[1].statement("Zed"), 1.0, "injected", 0)
    m.end_of_round(4)  # age 3: kept
    assert len(m) == 3
    m.end_of_round(5)  # age 4: learned item dropped
    assert {it.value for it in m.items} == {"Arden", "Zed"}


def test_bounded_evicts_lowest_confidence_then_oldest():
    m = Memory("bounded", capacity=2)
    m.write("a.x", "A", "The x of Aa is A.", 0.9, "base", 0)
    m.write("b.x", "B", "The x of Bb is B.", 0.3, "base", 1)
    m.write("c.x", "C", "The x of Cc is C.", 0.5, "base", 2)
    m.end_of_round(3)
    assert {it.value for it in m.items} == {"A", "C"}


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):
        Memory("forever")


def _ask(role, mem, msgs):
    sys_ = build_system("A0", role)
    return DeterministicMockLLM().generate(sys_, build_prompt(T.question, mem, msgs))


def test_mock_is_deterministic_and_reads_memory():
    a = _ask("worker", [(0.6, T.statement())], [])
    assert a == "Arden" == _ask("worker", [(0.6, T.statement())], [])


def test_mock_unknown_without_evidence():
    assert _ask("worker", [], []) == "UNKNOWN"
    assert _ask("worker", [(0.6, W[1].statement())], []) == "UNKNOWN"  # other fact only


def test_mock_weights_evidence():
    mem, msg = [(0.6, T.statement())], [(0.7, T.statement("Mira"))]
    assert _ask("worker", mem, msg) == "Mira"      # 0.7 > 0.6
    assert _ask("verifier", mem, msg) == "Arden"   # 1.5*0.6 > 0.75*0.7
    assert _ask("relay", mem, msg) == "Mira"
    assert _ask("worker", mem, [(0.5, T.statement("Mira"))]) == "Arden"


def test_mock_tie_prefers_older_memory():
    assert _ask("worker", [(0.6, T.statement()), (0.6, T.statement("Mira"))], []) == "Arden"


def test_roles_all_have_prompts():
    for r in ROLES:
        assert f"ROLE: {r}." in build_system("A1", r)


def test_parse_answer():
    assert parse_answer("The answer is arden.", ["Arden", "Mira"]) == "Arden"
    assert parse_answer("UNKNOWN", ["Arden"]) is None
    assert parse_answer("Mira, not Arden", ["Arden", "Mira"]) == "Mira"


def test_factory_and_optional_backends_fail_cleanly(monkeypatch):
    assert make_backend("mock").name == "mock"
    with pytest.raises(ValueError):
        make_backend("nope")
    for k in ("ACB_API_BASE", "ACB_API_KEY", "ACB_API_MODEL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError, match="ACB_API"):
        make_backend("api")


def test_api_backend_request_shape_without_network(monkeypatch):
    monkeypatch.setenv("ACB_API_BASE", "https://example.invalid/v1")
    monkeypatch.setenv("ACB_API_KEY", "dummy-not-a-real-key")
    monkeypatch.setenv("ACB_API_MODEL", "some-model")
    seen = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"choices": [{"message": {"content": " Arden "}}]}).encode()

    def fake_urlopen(req, timeout):
        seen["url"], seen["auth"], seen["body"] = req.full_url, req.get_header("Authorization"), json.loads(req.data)
        return FakeResp()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = make_backend("api").generate("sys", "prompt")
    assert out == "Arden"
    assert seen["url"] == "https://example.invalid/v1/chat/completions"
    assert seen["body"]["temperature"] == 0 and seen["auth"].startswith("Bearer ")


def test_hf_backend_chat_shape_without_weights(monkeypatch):
    seen = {}

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, name):
            seen["tokenizer"] = name
            return cls()

        def apply_chat_template(self, messages, add_generation_prompt, return_tensors):
            seen["messages"] = messages
            assert add_generation_prompt and return_tensors == "pt"
            return np.array([[10, 11]])

        def decode(self, ids, skip_special_tokens):
            assert ids.tolist() == [12] and skip_special_tokens
            return " Arden "

    class FakeModel:
        @classmethod
        def from_pretrained(cls, name):
            seen["model"] = name
            return cls()

        def eval(self):
            seen["eval"] = True

        def generate(self, ids, max_new_tokens, do_sample):
            assert max_new_tokens == 12 and not do_sample
            return np.array([[10, 11, 12]])

    transformers = types.ModuleType("transformers")
    transformers.AutoTokenizer = FakeTokenizer
    transformers.AutoModelForCausalLM = FakeModel

    @contextmanager
    def no_grad():
        yield

    torch = types.ModuleType("torch")
    torch.no_grad = no_grad
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", torch)

    from acb.llm.hf import HFBackend

    out = HFBackend("fictional/model").generate("system", "prompt")
    assert out == "Arden"
    assert seen["model"] == seen["tokenizer"] == "fictional/model"
    assert seen["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "prompt"},
    ]
