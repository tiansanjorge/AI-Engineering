"""Tests de las colecciones Chroma con embeddings falsos deterministas (sin API)."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.config import DOMAINS
from src.vector_store import (
    build_domain_store,
    collection_name,
    get_retriever,
    get_store,
)


@pytest.fixture
def embeddings():
    return DeterministicFakeEmbedding(size=64)


@pytest.fixture
def persist_dir(tmp_path):
    return tmp_path / "chroma"


def test_build_creates_one_collection_per_domain(persist_dir, embeddings):
    for domain in DOMAINS:
        store = build_domain_store(domain, persist_dir, embeddings)
        assert store._collection.name == collection_name(domain)
        assert store._collection.count() >= 50


def test_rebuild_is_idempotent(persist_dir, embeddings):
    first = build_domain_store("hr", persist_dir, embeddings)._collection.count()
    second = build_domain_store("hr", persist_dir, embeddings)._collection.count()
    assert first == second


def test_collections_are_isolated_by_domain(persist_dir, embeddings):
    build_domain_store("hr", persist_dir, embeddings)
    build_domain_store("tech", persist_dir, embeddings)
    hits = get_retriever(
        "tech", k=10, persist_dir=persist_dir, embeddings=embeddings
    ).invoke("vacaciones")
    assert hits and {h.metadata["domain"] for h in hits} == {"tech"}


def test_metadata_filter_restricts_results(persist_dir, embeddings):
    build_domain_store("finance", persist_dir, embeddings)
    retriever = get_retriever(
        "finance",
        k=20,
        metadata_filter={"format": "csv"},
        persist_dir=persist_dir,
        embeddings=embeddings,
    )
    hits = retriever.invoke("plan business")
    assert hits and {h.metadata["format"] for h in hits} == {"csv"}


def test_collection_uses_cosine_distance(persist_dir, embeddings):
    store = build_domain_store("hr", persist_dir, embeddings)
    doc = store.get(limit=1)["documents"][0]
    ((_, distance),) = store.similarity_search_with_score(doc, k=1)
    assert distance == pytest.approx(
        0.0, abs=1e-5
    )  # coseno: un texto contra si mismo ~ 0


def test_get_store_fails_clearly_when_not_built(persist_dir, embeddings):
    with pytest.raises(RuntimeError, match="build_index"):
        get_store("hr", persist_dir, embeddings)


def test_unknown_domain_is_rejected(persist_dir, embeddings):
    with pytest.raises(ValueError):
        get_store("legal", persist_dir, embeddings)
