"""Fixtures compartidos: indices reales con embeddings falsos y un LLM de prueba."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda

from src.config import DOMAINS
from src.vector_store import build_domain_store


class FakeLLM:
    """Simula un chat model con salida estructurada.

    `responder` recibe los mensajes del prompt y devuelve lo que el modelo "contestaria":
    una instancia del esquema, un dict, o lanza una excepcion para simular un fallo.
    """

    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def with_structured_output(self, schema):
        def run(messages):
            self.calls.append(messages)
            return self.responder(messages)

        return RunnableLambda(run)


@pytest.fixture(scope="session")
def indexed(tmp_path_factory):
    """Colecciones de los tres dominios construidas una sola vez con embeddings falsos."""
    persist_dir = tmp_path_factory.mktemp("chroma")
    embeddings = DeterministicFakeEmbedding(size=64)
    for domain in DOMAINS:
        build_domain_store(domain, persist_dir, embeddings)
    return {"persist_dir": persist_dir, "embeddings": embeddings}
