"""Colecciones Chroma persistentes: una por dominio, con similitud coseno y metadatos.

Las colecciones se reconstruyen desde `data/` (el directorio `chroma_db/` no se versiona).
"""

from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

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


def get_retriever(
    domain: str,
    k: int = DEFAULT_K,
    metadata_filter: dict | None = None,
    persist_dir: Path = CHROMA_DIR,
    embeddings: Embeddings | None = None,
) -> VectorStoreRetriever:
    """Retriever LangChain sobre la coleccion de un dominio, con filtro opcional por metadatos."""
    search_kwargs: dict = {"k": k}
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
    return get_store(domain, persist_dir, embeddings).as_retriever(
        search_kwargs=search_kwargs
    )
