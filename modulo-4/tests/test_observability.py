"""Observabilidad: conteo de tokens por etapa y manejo de errores en los spans. Sin red."""

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from src import observability
from src.observability import StageStats, TokenTracker, stage


def _llm_result(input_tokens, output_tokens):
    message = AIMessage(
        content="x",
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )
    return LLMResult(generations=[[ChatGeneration(message=message)]])


def test_token_tracker_acumula_todas_las_llamadas_incluidos_reintentos():
    stats = StageStats("extraction_agent")
    tracker = TokenTracker(stats)
    tracker.on_llm_end(_llm_result(100, 20))
    tracker.on_llm_end(
        _llm_result(150, 30)
    )  # segundo intento (reintento de validacion)
    assert (stats.llm_calls, stats.input_tokens, stats.output_tokens) == (2, 250, 50)
    assert stats.total_tokens == 300
    assert stats.as_metadata()["total_tokens"] == 300


def test_token_tracker_tolera_respuestas_sin_usage():
    stats = StageStats("x")
    TokenTracker(stats).on_llm_end(
        LLMResult(generations=[[ChatGeneration(message=AIMessage(content="x"))]])
    )
    assert stats.total_tokens == 0


def test_stage_mide_latencia_y_expone_la_config_de_langchain():
    with stage("demo", as_type="span", input={"a": 1}, run_name="demo_run") as st:
        assert st.config["run_name"] == "demo_run"
        assert (
            len(st.config["callbacks"]) == 2
        )  # handler de Langfuse + contador de tokens
        st.set_output({"ok": True})
    assert st.stats.latency_s >= 0


def test_stage_relanza_la_excepcion_sin_esconderla():
    with (
        pytest.raises(ValueError, match="boom"),
        stage("demo", as_type="agent", input={}, run_name="r"),
    ):
        raise ValueError("boom")


class _BrokenClient:
    """Cliente de Langfuse cuya red falla (credenciales invalidas, caida del servicio...)."""

    def get_trace_url(self, trace_id):
        raise RuntimeError("401 Unauthorized")

    def flush(self):
        raise RuntimeError("sin red")


def test_fallos_de_langfuse_no_rompen_el_resultado(monkeypatch):
    monkeypatch.setattr(observability, "get_client", lambda: _BrokenClient())
    assert observability.safe_trace_url("abc") is None  # sin link, pero sin excepcion
    observability.flush()  # tampoco lanza
    assert observability.safe_trace_url(None) is None
