"""Agente 2: Extraccion de cambios.

Rol: auditor de contratos. Recibe el mapa del agente 1 (handoff) mas los dos textos, y tiene la
responsabilidad EXCLUSIVA de aislar y describir cada cambio de la adenda, distinguiendo adicion,
eliminacion y modificacion.

Garantia de formato en dos capas:
  1. Structured output: se le pasa a la API el esquema de `ExtractionResult`; el modelo esta
     forzado a generar JSON con esa forma (previene casi todos los errores de formato).
  2. Validacion Pydantic propia + auto-reparacion: aun con la forma correcta el CONTENIDO puede
     ser invalido (lista vacia, resumen en blanco). Si falla, se le devuelve al modelo su propio
     error de validacion y se reintenta; si se agotan los intentos, se lanza un error claro.
"""

import openai
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src import config
from src.errors import ModelAPIError, OutputValidationError
from src.llm import build_chat_model
from src.models import ContractChangeOutput, ExtractionResult

SYSTEM_PROMPT = (
    "Sos un auditor de contratos de una firma de compliance legal, riguroso y esceptico. "
    "Tu unica responsabilidad es identificar, aislar y describir cada cambio que introduce la "
    "adenda sobre el contrato original. Recibis un mapa contextual preparado por un analista, "
    "el texto del contrato original y el texto de la adenda.\n\n"
    "Reglas:\n"
    "1. Reporta UN elemento por cada cambio aislado (una clausula o inciso afectado = un "
    "cambio). No agrupes cambios distintos ni partas uno solo en varios.\n"
    "2. Clasifica cada cambio: 'adicion' (texto o clausula nueva), 'eliminacion' (texto que se "
    "quita) o 'modificacion' (texto que sigue existiendo pero cambia de valor o redaccion).\n"
    "3. Verifica cada cambio contra los DOS textos: compara lo que dice el original con lo que "
    "dice la adenda. Si la adenda no cambia nada de una clausula, no la reportes.\n"
    "4. En 'description' copia literalmente los valores anteriores y nuevos (montos, fechas, "
    "paises, plazos), sin redondear ni reformular.\n"
    "5. En 'section' usa el identificador exacto de la clausula ('Cláusula Tercera') y, si el "
    "cambio es sobre un inciso, agregalo ('Cláusula Cuarta, inciso 4.3').\n"
    "6. En 'topic' usa una categoria legal o comercial breve (p. ej. 'Precio', 'Plazo y "
    "vigencia', 'Alcance territorial').\n"
    "7. 'summary_of_the_change' es un parrafo en prosa, preciso y completo, para un abogado.\n"
    "8. No inventes cambios ni datos. Si el mapa contextual informa alertas (inconsistencias o "
    "pasajes [ilegible]), cerra el resumen con una frase que empiece con 'Advertencia:' "
    "indicandolas; si no hay alertas, no agregues nada."
)

USER_TEMPLATE = (
    "=== MAPA CONTEXTUAL ===\n{context_map}\n\n"
    "=== CONTRATO ORIGINAL ===\n{original}\n\n"
    "=== ADENDA ===\n{amendment}\n\n"
    "Extrae los cambios."
)

RETRY_TEMPLATE = (
    "Tu respuesta anterior no paso la validacion del esquema:\n{error}\n"
    "Corregila y devolve la respuesta completa nuevamente, cumpliendo el esquema."
)


class ExtractionAgent:
    """Extrae los cambios y devuelve el contrato de salida ya validado."""

    def __init__(self, structured_llm=None, max_validation_retries: int | None = None):
        # include_raw=True devuelve {"raw", "parsed", "parsing_error"}: en vez de explotar ante
        # una salida invalida, podemos leer el error y reintentar con feedback.
        # `structured_llm` es inyectable para testear sin llamar a la API.
        self.structured_llm = structured_llm or build_chat_model(
            config.AGENT_MODEL
        ).with_structured_output(
            ExtractionResult, method="json_schema", include_raw=True
        )
        self.max_validation_retries = (
            config.MAX_VALIDATION_RETRIES
            if max_validation_retries is None
            else max_validation_retries
        )

    def run(
        self,
        context_map: str,
        original_text: str,
        amendment_text: str,
        run_config: RunnableConfig | None = None,
    ) -> ContractChangeOutput:
        """Contrato publico (3 campos) derivado del detalle; lo validado se re-valida al derivar."""
        return self.extract(
            context_map, original_text, amendment_text, run_config
        ).to_output()

    def extract(
        self,
        context_map: str,
        original_text: str,
        amendment_text: str,
        run_config: RunnableConfig | None = None,
    ) -> ExtractionResult:
        """Resultado detallado (con tipo de cada cambio), validado y con auto-reparacion."""
        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_TEMPLATE.format(
                    context_map=context_map,
                    original=original_text,
                    amendment=amendment_text,
                )
            ),
        ]
        last_error = "sin detalle"
        raw = None
        for _attempt in range(self.max_validation_retries + 1):
            try:
                out = self.structured_llm.invoke(messages, config=run_config)
            except openai.OpenAIError as exc:
                raise ModelAPIError(
                    f"Fallo la llamada al agente de extraccion: {type(exc).__name__}: {exc}"
                ) from exc

            raw = out.get("raw")
            parsed, parsing_error = out.get("parsed"), out.get("parsing_error")
            if parsing_error is None and parsed is not None:
                # Ya paso la validacion de `ExtractionResult` (forma + reglas de contenido).
                return parsed

            last_error = (
                str(parsing_error) or "el modelo no devolvio una salida estructurada"
            )
            # Self-healing: se agrega al dialogo lo que dijo el modelo y por que esta mal.
            if raw is not None:
                messages.append(raw)
            messages.append(
                HumanMessage(content=RETRY_TEMPLATE.format(error=last_error))
            )

        raise OutputValidationError(
            f"El agente de extraccion no produjo una salida valida tras "
            f"{self.max_validation_retries + 1} intentos. Ultimo error: {last_error}",
            raw_output=getattr(raw, "content", raw),
        )
