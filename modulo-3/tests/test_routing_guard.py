"""Tests de la guarda de recuperacion y de su integracion con el orquestador (sin API)."""

import pytest

from src.agents.orchestrator import Orchestrator, RouteDecision
from src.routing_guard import DEFAULT_MAX_DISTANCE, RetrievalGuard
from src.vector_store import get_store
from tests.conftest import FakeLLM
from tests.test_orchestrator import StubAgent, decision


class FakeGuard:
    """Guarda de prueba: devuelve un veredicto fijo y registra las consultas."""

    def __init__(self, verdict):
        self.verdict, self.questions = verdict, []

    def veto(self, question):
        self.questions.append(question)
        return self.verdict


def make(router_decision, guard):
    agents = {d: StubAgent(d) for d in ("hr", "tech", "finance")}
    llm = FakeLLM(lambda m: router_decision)
    return Orchestrator(agents=agents, llm=llm, guard=guard), agents


def test_guard_overrides_a_false_out_of_scope_and_routes_to_the_closest_domain():
    orchestrator, agents = make(
        decision("out_of_scope", 0.9), FakeGuard(("tech", 0.31))
    )
    result = orchestrator.run("¿cuánto tiempo guardan el buzón?")
    assert result.intent == "tech" and result.status == "answered"
    assert result.route_overridden and result.guard_distance == 0.31
    assert result.low_confidence  # la confianza se rebaja a <= 0.5
    assert "Corregido por recuperación" in result.reason
    assert agents["tech"].questions and not agents["hr"].questions


def test_guard_without_veto_keeps_out_of_scope():
    orchestrator, agents = make(decision("out_of_scope"), FakeGuard(None))
    result = orchestrator.run("¿quién ganó el mundial?")
    assert result.status == "out_of_scope" and not result.route_overridden
    assert not any(a.questions for a in agents.values())


def test_guard_is_only_consulted_when_the_router_says_out_of_scope():
    guard = FakeGuard(("finance", 0.2))
    orchestrator, _ = make(decision("hr"), guard)
    result = orchestrator.run("una consulta de hr")
    assert result.intent == "hr" and not result.route_overridden
    assert guard.questions == []


def test_orchestrator_without_guard_behaves_as_before():
    orchestrator, _ = make(decision("out_of_scope"), None)
    assert orchestrator.run("algo").status == "out_of_scope"


def test_router_decision_schema_is_unchanged_by_the_guard():
    assert set(RouteDecision.model_fields) == {
        "intent",
        "confidence",
        "reason",
        "also_involves",
    }


@pytest.fixture
def real_guard(indexed):
    stores = {
        d: get_store(d, indexed["persist_dir"], indexed["embeddings"])
        for d in ("hr", "tech", "finance")
    }
    return stores, indexed["embeddings"]


def test_closest_domain_picks_the_collection_with_the_nearest_chunk(real_guard):
    stores, embeddings = real_guard
    guard = RetrievalGuard(stores, embeddings)
    # Un texto identico a un chunk de tech tiene distancia ~0 a esa coleccion.
    text = stores["tech"].get(limit=1)["documents"][0]
    domain, distance = guard.closest_domain(text)
    assert domain == "tech" and distance == pytest.approx(0.0, abs=1e-5)


def test_veto_depends_on_the_threshold(real_guard):
    stores, embeddings = real_guard
    text = stores["finance"].get(limit=1)["documents"][0]
    assert RetrievalGuard(stores, embeddings).veto(text)[0] == "finance"
    assert RetrievalGuard(stores, embeddings, max_distance=0.0).veto(text) is None


def test_default_threshold_is_the_calibrated_midpoint():
    assert DEFAULT_MAX_DISTANCE == 0.43
