"""Fabrica del modelo de chat, compartida por el parser de vision y los dos agentes.

Centralizar la construccion garantiza que TODAS las llamadas a la API tengan el mismo timeout y la
misma politica de reintentos, y que no haya claves ni parametros duplicados en cada modulo.
"""

from langchain_openai import ChatOpenAI

from src import config


def build_chat_model(model: str, name: str | None = None) -> ChatOpenAI:
    # temperature=0: tareas de transcripcion y analisis legal piden el comportamiento mas
    # determinista posible (misma entrada, misma salida en lo posible).
    # max_retries: el cliente reintenta solo ante rate limit o errores 5xx, con espera creciente.
    # timeout: evita que el pipeline se cuelgue indefinidamente si la API no responde.
    # `name` es el nombre con el que la llamada aparece en Langfuse (si no, "ChatOpenAI").
    return ChatOpenAI(
        name=name,
        model=model,
        temperature=0,
        timeout=config.REQUEST_TIMEOUT_S,
        max_retries=config.MAX_API_RETRIES,
    )
