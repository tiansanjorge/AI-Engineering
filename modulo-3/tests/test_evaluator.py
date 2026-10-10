"""Tests del agente evaluador: reglas de calculo, contexto, Score API y camino de falla (sin red)."""

import httpx
import pytest
from langchain_core.callbacks import BaseCallbackHandler
from openai import APIConnectionError

from src.agents.orchestrator import OrchestratorResult
from src.agents.rag_agent import AgentResult, RetrievedChunk, SourceRef
from src.evaluator import (
    ClaimCheck,
    ContextChunk,
    JudgeVerdict,
    PartCheck,
    RawJudgment,
    compute_verdict,
    context_from_result,
    evaluate_result,
    evaluate_trace,
    judge_response,
    push_scores,
)
from tests.conftest import FakeLLM


def raw(
    parts=(True,), claims=((True, True),), justified=None, relevance=10, reason="r"
):
    return RawJudgment(
        question_parts=[
            PartCheck(part=f"p{i}", answered=a) for i, a in enumerate(parts)
        ],
        claims=[
            ClaimCheck(claim=f"c{i}", supported=s, quote="cita" if s else "", central=c)
            for i, (s, c) in enumerate(claims)
        ],
        abstention_justified=justified,
        relevance=relevance,
        reason=reason,
    )


def test_perfect_answer_scores_10():
    v = compute_verdict(raw(), "answered")
    assert (v.score, v.accuracy, v.completeness) == (10, 10, 10)
    assert v.evidence == ["cita"] and v.unsupported_claims == []


def test_wrong_central_claim_caps_accuracy_and_score():
    v = compute_verdict(raw(claims=[(False, True)]), "answered")
    assert v.accuracy == 1 and v.score <= 2
    assert v.unsupported_claims == ["c0"]


def test_invented_side_detail_is_penalized_but_less_than_a_wrong_central_claim():
    v = compute_verdict(raw(claims=[(True, True), (False, False)]), "answered")
    assert v.accuracy == 4 and 4 <= v.score <= 5


def test_half_answered_question_lowers_completeness_and_score():
    v = compute_verdict(raw(parts=[True, False]), "answered")
    assert v.completeness == 5 and v.score == 6
    assert v.unanswered_parts == ["p1"]


def test_irrelevant_answer_scores_low_even_if_faithful_to_its_source():
    v = compute_verdict(raw(parts=[False], relevance=1), "answered")
    assert v.score <= 2


def test_justified_abstention_is_good_and_unjustified_is_bad():
    good = compute_verdict(raw(parts=[], claims=[], justified=True), "abstained")
    bad = compute_verdict(raw(parts=[], claims=[], justified=False), "abstained")
    assert good.score == 9 and good.abstention_justified is True
    assert bad.score == 1 and bad.completeness == 1


def test_missing_justification_is_treated_as_unjustified():
    assert (
        compute_verdict(raw(parts=[], claims=[], justified=None), "abstained").score
        == 1
    )


def test_score_is_always_within_1_and_10():
    for parts in ([True], [False], []):
        for claims in ([(True, True)], [(False, True)], []):
            v = compute_verdict(raw(parts=parts, claims=claims), "answered")
            assert 1 <= v.score <= 10


def make_result(status="answered", with_agent=True):
    agent = AgentResult(
        domain="hr",
        question="q",
        answer="a",
        abstained=status == "abstained",
        sources=[SourceRef(chunk_id="hr:1", source="d.md", section="S")]
        if status == "answered"
        else [],
        retrieved=[
            RetrievedChunk(
                chunk_id="hr:1", section="S", distance=0.2, text="texto uno"
            ),
            RetrievedChunk(
                chunk_id="hr:2", section="T", distance=0.4, text="texto dos"
            ),
        ],
    )
    return OrchestratorResult(
        question="¿pregunta?",
        intent="hr" if with_agent else "out_of_scope",
        status=status,
        answer="respuesta",
        sources=agent.sources,
        agent_result=agent if with_agent else None,
    )


def test_context_marks_only_cited_chunks():
    ctx = context_from_result(make_result())
    assert [(c.chunk_id, c.cited) for c in ctx] == [("hr:1", True), ("hr:2", False)]
    assert context_from_result(make_result("out_of_scope", with_agent=False)) == []


@pytest.mark.parametrize("status", ["out_of_scope", "error"])
def test_only_rag_answers_are_scored(status):
    llm = FakeLLM(lambda m: raw())
    assert evaluate_result(make_result(status, with_agent=False), llm) is None
    assert llm.calls == []


def test_judge_receives_question_answer_and_marked_context():
    llm = FakeLLM(lambda m: raw())
    verdict = evaluate_result(make_result(), llm)
    text = llm.calls[0].to_string()
    assert verdict.score == 10
    assert "¿pregunta?" in text and "respuesta" in text
    assert "[hr:1] CITADO" in text and "[hr:2]\ntexto dos" in text


def test_abstention_is_labeled_for_the_judge():
    llm = FakeLLM(lambda m: raw(parts=[], claims=[], justified=True))
    evaluate_result(make_result("abstained"), llm)
    assert "se abstuvo" in llm.calls[0].to_string()


def test_judge_response_rejects_malformed_output():
    with pytest.raises(ValueError):
        judge_response(
            "q", "a", "answered", [ContextChunk("c", "t")], FakeLLM(lambda m: {"x": 1})
        )


class FakeClient:
    def __init__(self):
        self.scores = []

    def create_score(self, **kwargs):
        self.scores.append(kwargs)


def test_push_scores_registers_quality_and_dimensions_on_the_trace():
    client = FakeClient()
    verdict = JudgeVerdict(
        relevance=9, completeness=8, accuracy=10, score=9, reason="motivo"
    )
    push_scores("trace-1", verdict, client)
    by_name = {s["name"]: s for s in client.scores}
    assert set(by_name) == {
        "quality",
        "quality_relevance",
        "quality_completeness",
        "quality_accuracy",
    }
    assert (
        by_name["quality"]["value"] == 9.0 and by_name["quality"]["comment"] == "motivo"
    )
    assert all(
        s["trace_id"] == "trace-1" and s["data_type"] == "NUMERIC"
        for s in client.scores
    )


class DummyHandler(BaseCallbackHandler):
    def __init__(self, trace_context=None):
        self.trace_context = trace_context


@pytest.fixture
def no_langfuse(monkeypatch):
    monkeypatch.setattr("langfuse.langchain.CallbackHandler", DummyHandler)


def test_evaluate_trace_scores_the_given_trace(no_langfuse):
    client = FakeClient()
    verdict = evaluate_trace("trace-9", make_result(), FakeLLM(lambda m: raw()), client)
    assert verdict.score == 10
    assert {s["trace_id"] for s in client.scores} == {"trace-9"}


def test_evaluate_trace_failure_does_not_break_the_flow_and_is_flagged(no_langfuse):
    def boom(messages):
        raise APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com")
        )

    client = FakeClient()
    assert evaluate_trace("trace-9", make_result(), FakeLLM(boom), client) is None
    assert client.scores[0]["name"] == "quality_evaluator_failed"
    assert client.scores[0]["comment"] == "APIConnectionError"


def test_evaluate_trace_skips_results_without_a_rag_answer(no_langfuse):
    client = FakeClient()
    skipped = make_result("out_of_scope", False)
    assert evaluate_trace("t", skipped, FakeLLM(lambda m: raw()), client) is None
    assert client.scores == []
