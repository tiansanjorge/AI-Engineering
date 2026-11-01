"""Agentes: handoff, validacion con auto-reparacion y manejo de errores. Sin API real."""

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.errors import EmptyParseError, ModelAPIError, OutputValidationError
from src.models import ContractChangeOutput, ExtractedChange, ExtractionResult

RESUMEN = (
    "Se modifica el monto mensual de USD 2.500 a USD 2.800 y se extiende la vigencia."
)


class FakeChat:
    """Modelo de texto falso para el agente 1."""

    def __init__(self, content="MAPA", error=None):
        self.content, self.error, self.messages = content, error, None

    def invoke(self, messages, config=None):
        self.messages = messages
        if self.error:
            raise self.error
        return AIMessage(content=self.content)


class FakeStructured:
    """Modelo estructurado falso: devuelve en orden las respuestas {raw, parsed, parsing_error}."""

    def __init__(self, outputs=(), error=None):
        self.outputs, self.error, self.calls = list(outputs), error, []

    def invoke(self, messages, config=None):
        self.calls.append(list(messages))
        if self.error:
            raise self.error
        item = self.outputs.pop(0)
        if isinstance(
            item, Exception
        ):  # simula una falla del modelo/API en ese intento
            raise item
        return item


def _result():
    return ExtractionResult(
        changes=[
            ExtractedChange(
                section="Cláusula Tercera",
                change_type="modificacion",
                topic="Precio",
                description="El monto pasa de USD 2.500 a USD 2.800.",
            )
        ],
        summary_of_the_change=RESUMEN,
    )


def _ok():
    return {"raw": AIMessage(content="{}"), "parsed": _result(), "parsing_error": None}


def _bad(msg="changes: lista vacia"):
    return {
        "raw": AIMessage(content="{malo}"),
        "parsed": None,
        "parsing_error": ValueError(msg),
    }


def _api_error():
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return openai.APIConnectionError(request=request)


# --- Agente 1: contextualizacion -------------------------------------------------------------


def test_contextualizacion_recibe_ambos_textos_y_devuelve_el_mapa():
    llm = FakeChat("  MAPA CONTEXTUAL  ")
    mapa = ContextualizationAgent(llm=llm).run("TEXTO ORIGINAL", "TEXTO ADENDA")
    assert mapa == "MAPA CONTEXTUAL"
    system, human = llm.messages
    assert "NO enumeres" in system.content  # el agente 1 no extrae cambios
    assert "TEXTO ORIGINAL" in human.content and "TEXTO ADENDA" in human.content


def test_contextualizacion_mapa_vacio():
    with pytest.raises(EmptyParseError):
        ContextualizationAgent(llm=FakeChat("  ")).run("a", "b")


def test_contextualizacion_traduce_error_de_api():
    with pytest.raises(ModelAPIError, match="contextualizacion"):
        ContextualizationAgent(llm=FakeChat(error=_api_error())).run("a", "b")


# --- Agente 2: extraccion --------------------------------------------------------------------


def test_extraccion_usa_el_mapa_del_agente_1_y_devuelve_el_contrato():
    fake = FakeStructured([_ok()])
    out = ExtractionAgent(structured_llm=fake).run("MAPA-X", "ORIGINAL", "ADENDA")
    assert isinstance(out, ContractChangeOutput)
    assert out.sections_changed == ["Cláusula Tercera"]
    assert out.topics_touched == ["Precio"]
    # Handoff: lo que el agente 2 le manda al modelo incluye el mapa del agente 1.
    assert "MAPA-X" in fake.calls[0][1].content


def test_extraccion_se_autorrepara_devolviendo_el_error_al_modelo():
    fake = FakeStructured([_bad("changes: lista vacia"), _ok()])
    out = ExtractionAgent(structured_llm=fake).run("m", "o", "a")
    assert out.sections_changed == ["Cláusula Tercera"]
    assert len(fake.calls) == 2
    # El segundo intento incluye lo que dijo el modelo y el motivo del rechazo.
    retry_messages = fake.calls[1]
    assert "lista vacia" in retry_messages[-1].content
    assert retry_messages[-2].content == "{malo}"


def test_extraccion_agota_reintentos_y_lanza_error_claro():
    fake = FakeStructured([_bad(), _bad(), _bad()])
    agent = ExtractionAgent(structured_llm=fake, max_validation_retries=2)
    with pytest.raises(OutputValidationError, match="3 intentos") as exc:
        agent.run("m", "o", "a")
    assert exc.value.raw_output == "{malo}"  # queda la salida cruda para auditar
    assert len(fake.calls) == 3


def test_extraccion_sin_reintentos_falla_al_primer_error():
    fake = FakeStructured([_bad()])
    with pytest.raises(OutputValidationError):
        ExtractionAgent(structured_llm=fake, max_validation_retries=0).run(
            "m", "o", "a"
        )


def test_extraccion_parsed_vacio_sin_error_tambien_es_fallo():
    fake = FakeStructured(
        [{"raw": AIMessage(content="x"), "parsed": None, "parsing_error": None}] * 3
    )
    with pytest.raises(OutputValidationError):
        ExtractionAgent(structured_llm=fake).run("m", "o", "a")


def test_extraccion_traduce_error_de_api():
    with pytest.raises(ModelAPIError, match="extraccion"):
        ExtractionAgent(structured_llm=FakeStructured(error=_api_error())).run(
            "m", "o", "a"
        )


def test_extraccion_no_arrastra_el_resultado_de_la_corrida_anterior():
    agent = ExtractionAgent(
        structured_llm=FakeStructured([_ok(), _bad(), _bad(), _bad()])
    )
    agent.run("m", "o", "a")
    assert agent.last_result is not None and agent.last_attempts == 1
    with pytest.raises(OutputValidationError):
        agent.run("m", "o", "a")
    assert (
        agent.last_result is None
    )  # la segunda corrida fallo: no debe quedar la primera


class _SalidaDesbocada(openai.LengthFinishReasonError):
    """La API corta la respuesta por limite de longitud (se vio con 16.384 tokens de salida)."""

    def __init__(self):
        Exception.__init__(self, "length limit was reached")


def test_extraccion_se_recupera_de_una_salida_desbocada():
    fake = FakeStructured([_SalidaDesbocada(), _ok()])
    out = ExtractionAgent(structured_llm=fake).run("m", "o", "a")
    assert out.sections_changed == ["Cláusula Tercera"]
    # El segundo intento le pide concision al modelo.
    assert "limite de longitud" in fake.calls[1][-1].content


def test_salida_desbocada_persistente_es_un_error_claro_y_no_de_api():
    fake = FakeStructured([_SalidaDesbocada()] * 3)
    with pytest.raises(OutputValidationError, match="limite de longitud"):
        ExtractionAgent(structured_llm=fake, max_validation_retries=2).run(
            "m", "o", "a"
        )
    assert len(fake.calls) == 3
