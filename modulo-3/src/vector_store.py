"""Colecciones Chroma persistentes: una por dominio, con similitud coseno y metadatos.

Las colecciones se reconstruyen desde `data/` (el directorio `chroma_db/` no se versiona).
"""

from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from src.config import CHROMA_DIR, DEFAULT_K, DOMAINS, EMBEDDING_MODEL
from src.ingestion import load_domain

_COSINE = {"hnsw": {"space": "cosine"}}


def collection_name(domain: str) -> str:
    if domain not in DOMAINS:
        raise ValueError(f"Dominio desconocido: {domain!r}. Validos: {sorted(DOMAINS)}")
    return f"{domain}_docs"


def default_embeddings() -> Embeddings:
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def _open(domain: str, persist_dir: Path, embeddings: Embeddings) -> Chroma:
    return Chroma(
        collection_name=collection_name(domain),
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        collection_configuration=_COSINE,
    )


def build_domain_store(
    domain: str,
    persist_dir: Path = CHROMA_DIR,
    embeddings: Embeddings | None = None,
    data_dir: Path | None = None,
) -> Chroma:
    """Reconstruye desde cero la coleccion de un dominio (borra la anterior si existe).

    Los ids de los chunks son deterministas, asi que reconstruir dos veces deja el mismo estado.
    """
    embeddings = embeddings or default_embeddings()
    documents = load_domain(domain, data_dir) if data_dir else load_domain(domain)
    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        client.delete_collection(collection_name(domain))
    except NotFoundError:  # la coleccion todavia no existia
        pass
    store = _open(domain, persist_dir, embeddings)
    store.add_documents(documents, ids=[d.metadata["chunk_id"] for d in documents])
    return store


def get_store(
    domain: str, persist_dir: Path = CHROMA_DIR, embeddings: Embeddings | None = None
) -> Chroma:
    """Abre la coleccion de un dominio ya construida; falla con un mensaje claro si esta vacia."""
    store = _open(domain, persist_dir, embeddings or default_embeddings())
    if store._collection.count() == 0:
        raise RuntimeError(
            f"La coleccion '{collection_name(domain)}' esta vacia o no existe. "
            "Ejecutar: python scripts/build_index.py"
        )
    return store


class ScoredChromaRetriever(BaseRetriever):
    """Retriever sobre una coleccion Chroma que agrega `distance` (coseno) a cada chunk.

    Es un `BaseRetriever` de LangChain: Langfuse lo registra como una observacion de tipo
    retriever, y la distancia queda disponible para diagnosticar recuperaciones malas.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    store: Chroma
    k: int = DEFAULT_K
    metadata_filter: dict | None = None

    def _get_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> list[Document]:
        results = self.store.similarity_search_with_score(
            query, k=self.k, filter=self.metadata_filter
        )
        return [
            Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "distance": round(d, 4)},
            )
            for doc, d in results
        ]


def get_retriever(
    domain: str,
    k: int = DEFAULT_K,
    metadata_filter: dict | None = None,
    persist_dir: Path = CHROMA_DIR,
    embeddings: Embeddings | None = None,
) -> ScoredChromaRetriever:
    """Retriever LangChain sobre la coleccion de un dominio, con filtro opcional por metadatos."""
    store = get_store(domain, persist_dir, embeddings)
    return ScoredChromaRetriever(
        store=store,
        k=k,
        metadata_filter=metadata_filter or None,
        name=f"retriever_{domain}",
    )


def nearest_distance(store: Chroma, query_vector: list[float]) -> float:
    """Distancia coseno del chunk mas cercano de una coleccion a un vector ya calculado.

    Usa la coleccion de Chroma directamente (una sola llamada, sin volver a embeber la consulta).
    """
    result = store._collection.query(query_embeddings=[query_vector], n_results=1)
    return float(result["distances"][0][0])
