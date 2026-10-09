"""Tests de la instrumentacion con un cliente de Langfuse simulado (no se envia nada a la red)."""

from contextlib import contextmanager

import pytest

import src.observability as obs
from src.agents.orchestrator import OrchestratorResult


class FakeSpan:
    trace_id = "trace-123"

    def __init__(self):
        self.updates = []

    def update(self, **kwargs):
        self.updates.append(kwargs)


class FakeClient:
    def __init__(self):
        self.span = FakeSpan()
        self.started = []
        self.scores = []

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        self.started.append(kwargs)
        yield self.span

    def create_score(self, **kwargs):
        self.scores.append(kwargs)

    def get_trace_url(self, trace_id):
        return f"https://langfuse.test/traces/{trace_id}"


class FakeSystem:
    def __init__(self, intent="hr", error=None):
        self.intent, self.error, self.configs = intent, error, []

    def run(self, question, config=None):
        self.configs.append(config)
        if self.error:
            raise self.error
        return OrchestratorResult(
            question=question,
            intent=self.intent,
            confidence=0.9,
            reason="r",
            status="answered",
            answer="respuesta",
        )


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(obs, "get_client", lambda: fake)
    monkeypatch.setattr(obs, "CallbackHandler", lambda: "handler")
    return fake


def test_one_root_span_wraps_the_request_and_handler_is_passed_to_the_graph(client):
    system = FakeSystem()
    traced = obs.traced_query(
        "¿vacaciones?", system=system, user_id="u1", session_id="s1"
    )
    assert [s["name"] for s in client.started] == ["support-request"]
    assert client.started[0]["input"] == {"query": "¿vacaciones?"}
    assert system.configs == [{"callbacks": ["handler"]}]
    assert traced.trace_id == "trace-123" and traced.trace_url.endswith("trace-123")


def test_root_span_records_output_and_actual_intent_metadata(client):
    obs.traced_query("q", system=FakeSystem("tech"))
    update = client.span.updates[-1]
    assert update["output"]["intent"] == "tech"
    assert update["metadata"]["actual_intent"] == "tech"


def test_routed_intent_score_is_always_recorded(client):
    obs.traced_query("q", system=FakeSystem("finance"))
    assert client.scores == [
        {
            "trace_id": "trace-123",
            "name": "routed_intent",
            "value": "finance",
            "data_type": "CATEGORICAL",
        }
    ]


@pytest.mark.parametrize(("expected", "value"), [("hr", 1.0), ("tech", 0.0)])
def test_routing_correct_score_only_with_expected_intent(client, expected, value):
    obs.traced_query("q", system=FakeSystem("hr"), expected_intent=expected)
    correct = next(s for s in client.scores if s["name"] == "routing_correct")
    assert correct["value"] == value and correct["data_type"] == "BOOLEAN"
    assert expected in correct["comment"]


def test_errors_are_marked_in_the_trace_and_reraised(client):
    with pytest.raises(ValueError, match="vacía"):
        obs.traced_query(
            "", system=FakeSystem(error=ValueError("La consulta está vacía"))
        )
    assert client.span.updates[-1]["level"] == "ERROR"
    assert "ValueError" in client.span.updates[-1]["status_message"]
    assert client.scores == []  # no hay resultado que puntuar


def test_trace_metadata_values_are_strings():
    assert obs._stringify({"a": 1, "b": None, "c": True}) == {"a": "1", "c": "True"}
