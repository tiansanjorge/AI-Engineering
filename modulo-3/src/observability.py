"""Instrumentacion con Langfuse (SDK v4, basado en OpenTelemetry).

Un request del usuario = un trace. La jerarquia que se obtiene en Langfuse es:

    support-request                       (span raiz, creado aca)
    └── LangGraph                          (grafo del orquestador)
        ├── route -> orchestrator-routing  (cadena del router)
        │            └── ChatOpenAI        (generation: clasificacion)
        └── hr | tech | finance            (nodo del agente)
            └── <dominio>-agent            (span del agente)
                ├── retriever_<dominio>    (recuperacion de chunks)
                └── ChatOpenAI             (generation: respuesta)

Los spans de LangChain/LangGraph los crea el `CallbackHandler` de Langfuse; este modulo agrega
el span raiz, los atributos del trace y los scores.

Atributos conocidos antes de ejecutar (usuario, sesion, tags, intencion esperada) van en el trace
con `propagate_attributes`. Lo que se sabe despues (intencion ruteada, estado) se registra en el
span raiz y como scores filtrables (`routed_intent`, `routing_correct`), porque el SDK v4 ya no
permite modificar tags del trace una vez iniciado.
"""

from dataclasses import dataclass

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from src.agents.orchestrator import Orchestrator, OrchestratorResult
from src.multi_agent_system import get_system

TRACE_NAME = "support-request"


@dataclass
class TracedResult:
    result: OrchestratorResult
    trace_id: str
    trace_url: str | None


def _stringify(metadata: dict | None) -> dict[str, str]:
    """Langfuse exige metadatos de trace con valores de texto."""
    return {str(k): str(v) for k, v in (metadata or {}).items() if v is not None}


def traced_query(
    question: str,
    *,
    system: Orchestrator | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    expected_intent: str | None = None,
) -> TracedResult:
    """Ejecuta una consulta y la registra como un unico trace en Langfuse."""
    system = system or get_system()
    langfuse = get_client()
    trace_metadata = _stringify(
        {**(metadata or {}), "expected_intent": expected_intent}
    )

    with langfuse.start_as_current_observation(
        as_type="span", name=TRACE_NAME, input={"query": question}
    ) as root:
        try:
            with propagate_attributes(
                user_id=user_id,
                session_id=session_id,
                tags=tags,
                metadata=trace_metadata,
            ):
                result = system.run(question, {"callbacks": [CallbackHandler()]})
        except Exception as exc:
            # No se traga el error: queda marcado en el trace y se re-lanza.
            root.update(level="ERROR", status_message=f"{type(exc).__name__}: {exc}")
            raise
        root.update(
            output={
                "answer": result.answer,
                "status": result.status,
                "intent": result.intent,
            },
            metadata={
                "actual_intent": result.intent,
                "status": result.status,
                "low_confidence": result.low_confidence,
                "route_overridden": result.route_overridden,
                "also_involves": result.also_involves,
            },
        )
        trace_id = root.trace_id

    langfuse.create_score(
        trace_id=trace_id,
        name="routed_intent",
        value=result.intent or "error",
        data_type="CATEGORICAL",
    )
    if expected_intent is not None:
        langfuse.create_score(
            trace_id=trace_id,
            name="routing_correct",
            value=1.0 if result.intent == expected_intent else 0.0,
            data_type="BOOLEAN",
            comment=f"esperado={expected_intent} ruteado={result.intent}",
        )
    return TracedResult(result, trace_id, langfuse.get_trace_url(trace_id=trace_id))


def flush() -> None:
    """Envia los eventos pendientes (necesario en scripts de vida corta antes de salir)."""
    get_client().flush()
