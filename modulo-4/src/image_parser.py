"""Paso 1: de imagen a texto con un modelo de vision multimodal.

Por que un LLM de vision y no OCR tradicional: un OCR devuelve texto plano "suelto" y pierde la
estructura (que es un encabezado de clausula, que es un inciso). Un modelo multimodal ENTIENDE el
documento: conserva jerarquia, tolera rotacion y ruido, e infiere palabras parcialmente borrosas.

Principio de diseno: validar ANTES de gastar. Todo lo que se puede chequear en local (existe,
formato, peso, imagen no corrupta) se chequea sin llamar a la API.
"""

import base64
from pathlib import Path

import openai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from PIL import Image, UnidentifiedImageError

from src import config
from src.errors import EmptyParseError, InvalidImageError, VisionAPIError

# El prompt es una pieza de ingenieria: pide FIDELIDAD, no interpretacion. Un parser que
# "mejora" o resume el texto es peor que uno literal, porque los agentes siguientes comparan
# palabra por palabra (un monto o una fecha cambiados en silencio serian un cambio fantasma).
VISION_SYSTEM_PROMPT = (
    "Sos un sistema de transcripcion de documentos legales escaneados. Tu unica tarea es "
    "transcribir el texto de la imagen de la forma mas fiel posible.\n"
    "Reglas:\n"
    "1. Transcribi TODO el texto visible, en orden de lectura, sin omitir ni resumir nada.\n"
    "2. Conserva la estructura: el titulo, cada encabezado de clausula y cada inciso "
    "(4.1, 4.2...) en su propia linea; separa los bloques con una linea en blanco.\n"
    "3. Copia literalmente cifras, fechas, montos, nombres y numeros de clausula. No corrijas, "
    "no normalices ni reformules.\n"
    "4. Si una palabra o cifra es ilegible, escribi [ilegible]; nunca la adivines ni la inventes.\n"
    "5. Ignora el ruido visual (manchas, bordes, fondo, rotacion): no lo describas.\n"
    "6. Respondé solo con la transcripcion, sin comentarios, sin introduccion y sin formato "
    "markdown."
)
VISION_USER_PROMPT = "Transcribi el documento de la imagen."

# Mapeo del formato REAL detectado por Pillow (no de la extension) al tipo MIME del data URL.
_MIME_BY_FORMAT = {"PNG": "image/png", "JPEG": "image/jpeg"}


def validate_image(image_path: str | Path) -> Path:
    """Chequea el archivo en local y devuelve su Path; lanza InvalidImageError si no sirve."""
    path = Path(image_path)
    if not path.is_file():
        raise InvalidImageError(f"No existe el archivo de imagen: {path}")
    if path.suffix.lower() not in config.ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidImageError(
            f"Formato no soportado '{path.suffix}' (permitidos: "
            f"{', '.join(sorted(config.ALLOWED_IMAGE_EXTENSIONS))}): {path.name}"
        )
    size = path.stat().st_size
    if size == 0:
        raise InvalidImageError(f"El archivo esta vacio: {path.name}")
    if size > config.MAX_IMAGE_MB * 1024 * 1024:
        raise InvalidImageError(
            f"La imagen pesa {size / 1024 / 1024:.1f} MB y el maximo es {config.MAX_IMAGE_MB} MB: "
            f"{path.name}"
        )
    return path


def encode_image(path: Path) -> str:
    """Devuelve la imagen como data URL base64 (`data:image/png;base64,...`).

    base64 permite mandar la imagen dentro del mismo request, sin hostearla en una URL publica.
    Se abre con Pillow para detectar archivos corruptos o con extension falsa (p. ej. un .txt
    renombrado a .png) antes de pagar una llamada a la API.
    """
    try:
        with Image.open(path) as img:
            img.verify()  # chequea integridad sin decodificar todo
            fmt = img.format
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError(
            f"El archivo no es una imagen valida: {path.name} ({exc})"
        ) from exc
    mime = _MIME_BY_FORMAT.get(fmt or "")
    if mime is None:
        raise InvalidImageError(
            f"Formato real '{fmt}' no soportado (solo PNG/JPEG): {path.name}"
        )
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _build_llm() -> ChatOpenAI:
    # temperature=0: una transcripcion debe ser lo mas determinista posible.
    # max_retries / timeout: el cliente reintenta solo ante rate limit o errores 5xx y no se
    # cuelga indefinidamente si la API no responde.
    return ChatOpenAI(
        model=config.VISION_MODEL,
        temperature=0,
        timeout=config.REQUEST_TIMEOUT_S,
        max_retries=config.MAX_API_RETRIES,
    )


def parse_contract_image(
    image_path: str | Path,
    *,
    run_config: RunnableConfig | None = None,
    llm=None,
) -> str:
    """Extrae el texto completo de una imagen de contrato con el modelo de vision.

    `run_config` lleva los callbacks de Langfuse (para que la llamada quede trazada con tokens y
    latencia). `llm` permite inyectar un modelo falso en los tests, sin llamar a la API.
    """
    path = validate_image(image_path)
    data_url = encode_image(path)
    llm = llm or _build_llm()

    messages = [
        SystemMessage(content=VISION_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {"type": "text", "text": VISION_USER_PROMPT},
                # detail="high": la imagen se procesa en mosaicos de alta resolucion. Cuesta mas
                # tokens pero es lo que permite leer letra chica y escaneos degradados.
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ]
        ),
    ]
    try:
        response = llm.invoke(messages, config=run_config)
    except openai.OpenAIError as exc:
        # Ya se agotaron los reintentos del cliente: se traduce a un error del dominio.
        raise VisionAPIError(
            f"Fallo la llamada a la API de vision para {path.name}: {type(exc).__name__}: {exc}"
        ) from exc

    content = response.content
    text = content if isinstance(content, str) else ""
    text = text.strip()
    if not text:
        raise EmptyParseError(f"El modelo no devolvio texto para {path.name}")
    return text


def image_size(image_path: str | Path) -> tuple[int, int]:
    """Dimensiones en pixeles (se usa como metadata de la traza)."""
    with Image.open(image_path) as img:
        return img.size
