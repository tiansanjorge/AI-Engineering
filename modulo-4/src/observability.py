"""Trazabilidad con Langfuse (SDK v4, basado en OpenTelemetry).

Un analisis de contratos = un trace, con esta jerarquia (nombres fijados por la consigna):

    contract-analysis                      (span raiz: toda la ejecucion)
    ├── parse_original_contract            (span)  └── generation: transcripcion de vision
    ├── parse_amendment_contract           (span)  └── generation: transcripcion de vision
    ├── contextualization_agent            (agent) └── generation: mapa contextual
    └── extraction_agent                   (agent) └── generation(es): extraccion (+ reintentos)

Division de trabajo:
  - Los spans de etapa los creamos nosotros (este modulo): son las "cajas" del pipeline.
  - Las llamadas al LLM (las `generation`) las registra el CallbackHandler de LangChain, ya con
    modelo, tokens y costo; quedan anidadas bajo la etapa activa.
  - Ademas contamos los tokens por nuestra cuenta (`TokenTracker`) para mostrar un resumen en la
    terminal sin depender de consultar Langfuse.

Principio: la observabilidad NO debe romper la aplicacion. El SDK envia en segundo plano y no
lanza errores de red; si falta la configuracion, el pipeline igual corre.
"""

import contextlib
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig
from langfuse import get_client
from langfuse.langchain import CallbackHandler


@dataclass
class StageStats:
    """Metricas de una etapa del pipeline (lo que se muestra al final en la terminal)."""

    name: str
    latency_s: float = 0.0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_metadata(self) -> dict:
        return {
            "latency_s": round(self.latency_s, 3),
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenTracker(BaseCallbackHandler):
    """Suma los tokens de cada llamada al LLM de una etapa (incluidos los reintentos)."""

    def __init__(self, stats: StageStats):
        self.stats = stats

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                usage = getattr(message, "usage_metadata", None) or {}
                self.stats.llm_calls += 1
                self.stats.input_tokens += usage.get("input_tokens", 0)
                self.stats.output_tokens += usage.get("output_tokens", 0)


class Stage:
    """Etapa activa del pipeline: expone la config de LangChain y permite fijar el output."""

    def __init__(self, span, name: str, run_name: str):
        self.span = span
        self.stats = StageStats(name)
        # Se crean DENTRO del span de la etapa para que las generations queden anidadas ahi.
        # `run_name` da un nombre descriptivo a la llamada (en vez del generico "ChatOpenAI").
        self.config: RunnableConfig = {
            "callbacks": [CallbackHandler(), TokenTracker(self.stats)],
            "run_name": run_name,
        }

    def set_output(self, output) -> None:
        self.span.update(output=output)


@contextmanager
def stage(
    name: str,
    *,
    as_type: str,
    input: dict,
    run_name: str,
    metadata: dict | None = None,
) -> Iterator[Stage]:
    """Abre un span hijo para una etapa y mide su latencia.

    Si la etapa falla, el span queda marcado como ERROR (visible y filtrable en el dashboard) y
    la excepcion se re-lanza: la traza documenta el fallo pero no lo esconde.
    """
    start = time.perf_counter()
    with get_client().start_as_current_observation(
        as_type=as_type, name=name, input=input, metadata=metadata
    ) as span:
        current = Stage(span, name, run_name)
        try:
            yield current
        except Exception as exc:
            span.update(level="ERROR", status_message=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            current.stats.latency_s = time.perf_counter() - start
            # La latencia y los tokens quedan como metadata filtrable del span.
            span.update(metadata={**(metadata or {}), **current.stats.as_metadata()})


def safe_trace_url(trace_id: str | None) -> str | None:
    """URL de la traza, o None si no se puede obtener.

    Obtenerla requiere una llamada de red a Langfuse (para conocer el id del proyecto) que falla
    con credenciales ausentes o invalidas. Como el analisis YA se hizo (y se pagaron los tokens),
    un fallo de observabilidad no puede costar el resultado: se degrada a "sin link".
    """
    if not trace_id:
        return None
    try:
        return get_client().get_trace_url(trace_id=trace_id)
    except Exception:  # noqa: BLE001 - la observabilidad nunca debe romper el analisis
        return None


def flush() -> None:
    """Envia los eventos pendientes. Imprescindible en scripts de vida corta: el SDK manda en
    segundo plano y, si el proceso termina antes, las trazas se pierden. Nunca lanza: perder una
    traza es preferible a perder el resultado del analisis."""
    with contextlib.suppress(Exception):
        get_client().flush()
