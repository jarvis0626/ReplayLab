"""Offline transport and grounding tests; never calls a live Meta model."""

import copy
import json

import httpx
import pytest

from app.digital_schemas import ScreenResult, ScreenRuleResult
from app.providers.grounded_explanation import clear_explanation_cache, explain_verification
from app.providers.meta import MetaProvider
from app.schemas import Step


@pytest.fixture(autouse=True)
def clear_cache():
    clear_explanation_cache()
    yield
    clear_explanation_cache()


def result():
    return ScreenResult(
        step_id="s1", status="fail", provider_mode="meta", explanation="The wrong panel is visible.",
        evidence=["Visible active panel: Preferences"],
        rule_results=[ScreenRuleResult(
            rule_id="r1", status="fail", expected="Extensions", observed="Preferences",
            correction="Open the reviewed Extensions panel.",
        )],
    )


def provider(tmp_path, plan, status=200):
    calls = []

    def handler(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == "muse-spark-1.3" and payload["store"] is False
        assert request.headers["Authorization"] == "Bearer test-explanation-only"
        assert str(request.url) == "https://api.meta.ai/v1/responses"
        assert payload["text"]["format"]["strict"] is True
        assert "immutable" in payload["instructions"]
        assert all(item["type"] == "input_text" for item in payload["input"][0]["content"])
        return httpx.Response(status, json={"status": "completed", "output": [{
            "type": "message", "content": [{"type": "output_text", "text": json.dumps(plan)}],
        }]})

    return MetaProvider("test-explanation-only", tmp_path / "unused-cache",
                        client=httpx.Client(transport=httpx.MockTransport(handler))), calls


def test_muse_selects_grounded_natural_language_without_mutating_decision(tmp_path):
    decision = result()
    before = copy.deepcopy(decision.model_dump())
    live, calls = provider(tmp_path, {"status": "fail", "evidence_ids": ["E1"], "correction_id": "C1"})
    explanation = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert explanation.provider_mode == "meta_grounded_plan" and explanation.status == "fail"
    assert "Preferences" in explanation.text and "Next: Open" in explanation.text
    assert explanation.evidence_ids == ("E1",) and explanation.latency_ms >= 0
    assert decision.model_dump() == before and len(calls) == 1
    assert not (tmp_path / "unused-cache").exists()


@pytest.mark.parametrize("plan", [
    {"status": "pass", "evidence_ids": ["E1"], "correction_id": "C1"},
    {"status": "fail", "evidence_ids": ["invented"], "correction_id": None},
    {"status": "fail", "evidence_ids": ["E1"], "correction_id": "invented"},
    {"status": "fail", "evidence_ids": [], "correction_id": [], "narration": "invented fact"},
    {"status": "fail", "evidence_ids": "E1", "correction_id": None},
])
def test_invented_evidence_or_changed_verdict_is_rejected(tmp_path, plan):
    live, _ = provider(tmp_path, plan)
    decision = result()
    explanation = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert explanation.text == decision.explanation
    assert explanation.provider_mode == "deterministic_template" and explanation.warning
    assert decision.status == "fail"


@pytest.mark.parametrize("code", [402, 403, 429])
def test_unavailable_explanation_keeps_explicit_template_without_changing_inference(tmp_path, code, monkeypatch):
    monkeypatch.setattr("app.providers.meta.time.sleep", lambda _: None)
    live, _ = provider(tmp_path, {}, status=code)
    decision = result()
    explanation = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert explanation.warning and explanation.text == decision.explanation
    assert decision.provider_mode == "meta" and decision.status == "fail"


def test_ram_cache_and_redaction_do_not_write_screen_evidence_to_disk(tmp_path):
    live, calls = provider(tmp_path, {"status": "fail", "evidence_ids": ["E1"], "correction_id": None})
    decision = result()
    decision.evidence = ["Account person@example.invalid shows Preferences"]
    first = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    second = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert first.cache_hit is False and second.cache_hit is True and len(calls) == 1
    assert "person@example.invalid" not in first.text
    assert b"person@example.invalid" not in calls[0].content
    clear_explanation_cache()
    explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert len(calls) == 2


def test_offline_template_never_sends_a_request():
    decision = result()
    explanation = explain_verification(None, Step(id="s1", title="Open Extensions"), decision)
    assert explanation.provider_mode == "deterministic_template" and explanation.warning is None
    assert explanation.text == decision.explanation


def test_pass_cannot_select_a_recovery_instruction(tmp_path):
    decision = result()
    decision.status = "pass"
    live, _ = provider(tmp_path, {"status": "pass", "evidence_ids": ["E1"], "correction_id": "C1"})
    explanation = explain_verification(live, Step(id="s1", title="Open Extensions"), decision)
    assert explanation.warning and explanation.status == "pass"
