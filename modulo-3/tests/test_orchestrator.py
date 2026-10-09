"""Tests del orquestador con router y agentes simulados. No llaman a ninguna API."""

import httpx
import pytest
from openai import APIConnectionError

from src.agents.orchestrator import (
    ESCALATION_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    Orchestrator,
    RouteDecision,
)
from src.agents.rag_agent import AgentResult, SourceRef
from tests.conftest import FakeLLM


class StubAgent:
    """Agente de prueba: registra las consultas que recibe y devuelve un resultado fijo."""

    def __init__(self, domain, abstained=False, error=None):
        self.domain, self.abstained, self.error = domain, abstained, error
        self.questions = []

    def answer(self, question, config=None):
        self.questions.append(question)
        sources = (
            []
            if self.abstained
            else [
                SourceRef(chunk_id=f"{self.domain}:x:1", source="d/x.md", section="S")
            ]
        )
        return AgentResult(
            domain=self.domain,
            question=question,
            answer=f"respuesta {self.domain}",
            abstained=self.abstained,
            sources=sources,
            error=self.error,
        )


def decision(intent, confidence=0.9, also=()):
    return RouteDecision(
        intent=intent,
        confidence=confidence,
        reason="porque sí",
        also_involves=list(also),
    )


def make(router_output, **stub_kwargs):
    agents = {
        d: StubAgent(d, **stub_kwargs.get(d, {})) for d in ("hr", "tech", "finance")
    }
    llm = FakeLLM(
        router_output if callable(router_output) else (lambda m: router_output)
    )
    return Orchestrator(agents=agents, llm=llm), agents, llm


@pytest.mark.parametrize("intent", ["hr", "tech", "finance"])
def test_routes_to_exactly_one_agent(intent):
    orchestrator, agents, _ = make(decision(intent))
    result = orchestrator.run("una consulta")
    assert result.status == "answered" and result.intent == intent
    assert result.answer == f"respuesta {intent}"
    assert [d for d, a in agents.items() if a.questions] == [intent]
    assert result.sources and result.agent_result.domain == intent


def test_out_of_scope_does_not_call_any_agent():
    orchestrator, agents, _ = make(decision("out_of_scope"))
    result = orchestrator.run("cláusula del contrato")
    assert result.status == "out_of_scope" and result.answer == OUT_OF_SCOPE_MESSAGE
    assert not any(a.questions for a in agents.values())
    assert result.sources == [] and result.agent_result is None


def test_router_prompt_contains_question_categories_and_examples():
    orchestrator, _, llm = make(decision("hr"))
    orchestrator.run("¿Cuándo cobro?")
    text = llm.calls[0].to_string()
    assert "¿Cuándo cobro?" in text
    for category in ("hr:", "tech:", "finance:", "out_of_scope:"):
        assert category in text
    assert "Ejemplos" in text


def test_secondary_areas_add_a_note_and_never_repeat_the_primary():
    orchestrator, _, _ = make(decision("tech", also=["finance", "tech", "finance"]))
    result = orchestrator.run("no puedo entrar a Nimbus Expenses")
    assert result.also_involves == ["finance"]
    assert "también involucra a Finanzas" in result.answer


def test_no_note_when_the_agent_abstains():
    orchestrator, _, _ = make(decision("hr", also=["tech"]), hr={"abstained": True})
    result = orchestrator.run("algo")
    assert result.status == "abstained" and "Nota:" not in result.answer


def test_low_confidence_is_flagged_but_still_routed():
    orchestrator, agents, _ = make(decision("finance", confidence=0.4))
    result = orchestrator.run("algo ambiguo")
    assert result.low_confidence and result.status == "answered"
    assert agents["finance"].questions


def test_agent_error_is_propagated_in_the_result():
    orchestrator, _, _ = make(
        decision("tech"), tech={"abstained": True, "error": "Fallo del modelo: X"}
    )
    result = orchestrator.run("algo")
    assert result.status == "abstained" and result.error == "Fallo del modelo: X"


@pytest.mark.parametrize(
    "bad_output",
    [
        {"intent": "legal", "confidence": 0.9, "reason": "x"},  # categoria inexistente
        {"intent": "hr", "confidence": 7, "reason": "x"},  # confianza fuera de rango
        {"reason": "falta intent"},
    ],
)
def test_invalid_router_output_escalates_instead_of_guessing(bad_output):
    orchestrator, agents, _ = make(bad_output)
    result = orchestrator.run("algo")
    assert result.status == "error" and result.answer == ESCALATION_MESSAGE
    assert result.intent is None and "inválida" in result.error
    assert not any(a.questions for a in agents.values())


def test_router_provider_failure_escalates():
    def boom(messages):
        raise APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com")
        )

    orchestrator, agents, _ = make(boom)
    result = orchestrator.run("algo")
    assert result.status == "error" and "APIConnectionError" in result.error
    assert not any(a.questions for a in agents.values())


@pytest.mark.parametrize("question", ["", "   ", None, "x" * 2001])
def test_invalid_questions_are_rejected_before_any_model_call(question):
    orchestrator, _, llm = make(decision("hr"))
    with pytest.raises(ValueError):
        orchestrator.run(question)
    assert llm.calls == []


def test_graph_has_conditional_routing_to_every_branch():
    orchestrator, _, _ = make(decision("hr"))
    mermaid = orchestrator.draw_mermaid()
    for node in (
        "route",
        "hr",
        "tech",
        "finance",
        "finalize",
        "out_of_scope",
        "escalate",
    ):
        assert node in mermaid


def test_end_to_end_with_real_agents_and_fake_models(indexed):
    from src.agents.rag_agent import LLMAnswer
    from tests.test_rag_agent import first_ids

    def responder(messages):
        text = messages.to_string()
        if "orquestador" in text:
            return decision("tech")
        return LLMAnswer(
            answer="Reiniciá el cliente.",
            source_ids=first_ids(messages, 1),
        )

    llm = FakeLLM(responder)
    from src.agents.registry import build_agents

    agents = build_agents(
        llm, persist_dir=indexed["persist_dir"], embeddings=indexed["embeddings"]
    )
    result = Orchestrator(agents=agents, llm=llm).run("La VPN se corta")
    assert result.status == "answered" and result.intent == "tech"
    assert result.sources[0].chunk_id.startswith("tech:")
    assert {r.chunk_id.split(":")[0] for r in result.agent_result.retrieved} == {"tech"}


def test_out_of_scope_listed_in_also_involves_is_ignored_not_a_crash():
    orchestrator, _, _ = make(decision("tech", also=["out_of_scope", "finance"]))
    result = orchestrator.run("algo")
    assert result.status == "answered"
    assert result.also_involves == ["finance"]
    assert "out_of_scope" not in result.answer
