"""Tests de los agentes RAG con un LLM simulado. No llaman a ninguna API."""

import httpx
import pytest
from openai import APIConnectionError

from src.agents.rag_agent import LLMAnswer, RAGAgent
from src.agents.registry import build_agents
from src.vector_store import get_retriever
from tests.conftest import FakeLLM


def make_agent(indexed, llm, domain="hr", k=4):
    retriever = get_retriever(
        domain,
        k=k,
        persist_dir=indexed["persist_dir"],
        embeddings=indexed["embeddings"],
    )
    return RAGAgent(domain, "Recursos Humanos", "Nota de alcance.", retriever, llm)


def first_ids(messages, n=2):
    """Extrae los chunk_id del contexto que recibio el modelo, en orden."""
    import re

    text = messages.to_string() if hasattr(messages, "to_string") else str(messages)
    return re.findall(r"^\[([\w:.\-]+)\]", text, flags=re.MULTILINE)[:n]


def test_answer_cites_only_retrieved_chunks_with_metadata(indexed):
    llm = FakeLLM(lambda m: LLMAnswer(answer="Respuesta.", source_ids=first_ids(m)))
    result = make_agent(indexed, llm).answer("¿Cuántos días de vacaciones me tocan?")
    assert not result.abstained and result.error is None
    assert len(result.sources) == 2
    assert all(
        s.chunk_id.startswith("hr:") and s.source.startswith("hr_docs/")
        for s in result.sources
    )
    assert len(result.retrieved) == 4
    assert all(r.distance >= 0 for r in result.retrieved)


def test_prompt_includes_context_question_and_scope(indexed):
    llm = FakeLLM(lambda m: LLMAnswer(answer="x", source_ids=[]))
    make_agent(indexed, llm).answer("¿Cuándo cobro?")
    text = llm.calls[0].to_string()
    assert (
        "¿Cuándo cobro?" in text
        and "Nota de alcance." in text
        and "Recursos Humanos" in text
    )
    assert text.count("[hr:") >= 4  # los 4 fragmentos recuperados, con su chunk_id


def test_invented_source_ids_are_dropped(indexed):
    llm = FakeLLM(
        lambda m: LLMAnswer(
            answer="Respuesta.",
            source_ids=[*first_ids(m, 1), "hr:inventado:999"],
        )
    )
    result = make_agent(indexed, llm).answer("¿Vacaciones?")
    assert not result.abstained
    assert [s.chunk_id for s in result.sources] == first_ids(llm.calls[0], 1)


def test_answer_with_only_invented_sources_is_discarded(indexed):
    llm = FakeLLM(
        lambda m: LLMAnswer(answer="Dato inventado.", source_ids=["hr:fake:1"])
    )
    result = make_agent(indexed, llm).answer("¿Vacaciones?")
    assert result.abstained and result.sources == []
    assert "Dato inventado" not in result.answer
    assert "documentación de Recursos Humanos" in result.answer
    assert result.error


def test_no_sources_means_abstention_and_keeps_the_models_explanation(indexed):
    llm = FakeLLM(lambda m: LLMAnswer(answer="No encuentro eso.", source_ids=[]))
    result = make_agent(indexed, llm).answer("¿Capital de Marte?")
    assert result.abstained and result.sources == [] and result.error is None
    assert result.answer == "No encuentro eso."


def test_evidence_decides_abstention_not_the_models_hedging(indexed):
    """Si el modelo duda en el texto pero cita un fragmento valido, la respuesta cuenta."""
    llm = FakeLLM(
        lambda m: LLMAnswer(
            answer="No hay un dato específico, pero en general son 30 días.",
            source_ids=first_ids(m, 1),
        )
    )
    result = make_agent(indexed, llm).answer("¿Plazo del reembolso?")
    assert not result.abstained and len(result.sources) == 1


def test_malformed_model_output_becomes_abstention_not_crash(indexed):
    llm = FakeLLM(lambda m: {"answer": "sin campos requeridos"})
    result = make_agent(indexed, llm).answer("¿Vacaciones?")
    assert result.abstained and "inválida" in result.error
    assert result.retrieved  # la traza de la recuperacion se conserva


def test_provider_failure_becomes_abstention_not_crash(indexed):
    def boom(messages):
        raise APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com")
        )

    result = make_agent(indexed, FakeLLM(boom)).answer("¿Vacaciones?")
    assert result.abstained and "APIConnectionError" in result.error


@pytest.mark.parametrize("question", ["", "   ", None])
def test_empty_question_is_rejected(indexed, question):
    llm = FakeLLM(lambda m: LLMAnswer(answer="x", source_ids=[]))
    with pytest.raises(ValueError):
        make_agent(indexed, llm).answer(question)
    assert llm.calls == []  # no se gasta una llamada al modelo


def test_registry_builds_three_isolated_agents(indexed):
    llm = FakeLLM(lambda m: LLMAnswer(answer="x", source_ids=first_ids(m, 1)))
    agents = build_agents(
        llm, persist_dir=indexed["persist_dir"], embeddings=indexed["embeddings"]
    )
    assert set(agents) == {"hr", "tech", "finance"}
    for domain, agent in agents.items():
        result = agent.answer("consulta cualquiera")
        assert {r.chunk_id.split(":")[0] for r in result.retrieved} == {domain}
        assert result.domain == domain
    prompts = {agent.area for agent in agents.values()}
    assert len(prompts) == 3
