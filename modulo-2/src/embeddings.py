"""Generacion de embeddings via la API de OpenAI."""

import os

from openai import OpenAI

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def get_client() -> OpenAI:
    """Cliente de OpenAI. Lee OPENAI_API_KEY del entorno (nunca hardcodeada)."""
    return OpenAI()


def generate_embeddings(
    texts: list[str], model: str = DEFAULT_EMBEDDING_MODEL
) -> list[list[float]]:
    """Etapa 3 del pipeline de indexacion: convierte una lista de chunks
    en su representacion vectorial. Una sola llamada a la API para todos
    los chunks (mas barato y mas rapido que uno por uno)."""
    client = get_client()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def embed_query(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> list[float]:
    """Convierte una sola pregunta de usuario en su embedding."""
    return generate_embeddings([text], model=model)[0]
