"""Tests del pipeline de chunking, busqueda vectorial y consulta.

Ninguno llama a la API real: embed_query y generate_answer se mockean
con monkeypatch, igual que en el Modulo 1. Corren rapido, gratis, y sin
necesitar OPENAI_API_KEY configurada.
"""

import json
import os

import numpy as np
import pytest

import query
from chunking import DEFAULT_DOCUMENT_PATH, chunk_text, load_and_chunk_document
from vector_store import cosine_similarity, load_index, save_index, search_similar_chunks


# ---------------------------------------------------------------------------
# chunking.py
# ---------------------------------------------------------------------------

def test_chunk_text_respects_chunk_size():
    text = " ".join(f"palabra{i}" for i in range(250))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    # el primer chunk siempre tiene exactamente chunk_size palabras (hay
    # suficiente texto); ningun chunk supera ese tamano.
    assert len(chunks[0].split()) == 100
    assert all(len(chunk.split()) <= 100 for chunk in chunks)


def test_chunk_text_overlaps_between_consecutive_chunks():
    text = " ".join(f"palabra{i}" for i in range(150))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    # las ultimas 20 palabras del primer chunk son las primeras 20 del segundo
    assert chunks[0].split()[-20:] == chunks[1].split()[:20]


def test_chunk_text_rejects_overlap_gte_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("cualquier texto", chunk_size=50, overlap=50)


def test_load_and_chunk_document_generates_at_least_20_chunks():
    # Corre contra el documento fuente real (data/faq_document.txt), no
    # un texto sintetico: es la verificacion de que el documento entregado
    # efectivamente cumple el minimo que pide la consigna.
    chunks = load_and_chunk_document(DEFAULT_DOCUMENT_PATH, chunk_size=100, overlap=20)
    assert len(chunks) >= 20


def test_load_and_chunk_document_chunk_sizes_within_token_range():
    # Aproximamos tokens con palabras * 1.3 (relacion tipica para
    # espaniol). El chunk_size=100 esta bien adentro de 50-500 tokens
    # incluso en el peor caso (el ultimo chunk, mas corto).
    chunks = load_and_chunk_document(DEFAULT_DOCUMENT_PATH, chunk_size=100, overlap=20)
    for chunk in chunks:
        estimated_tokens = len(chunk.split()) * 1.3
        assert 50 <= estimated_tokens <= 500


# ---------------------------------------------------------------------------
# vector_store.py
# ---------------------------------------------------------------------------

def test_cosine_similarity_identical_vectors_is_one():
    vector = np.array([1.0, 2.0, 3.0])
    matrix = np.array([vector])
    similarity = cosine_similarity(vector, matrix)[0]
    assert similarity == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    query_vector = np.array([1.0, 0.0])
    matrix = np.array([[0.0, 1.0]])
    similarity = cosine_similarity(query_vector, matrix)[0]
    assert similarity == pytest.approx(0.0)


def test_search_similar_chunks_returns_k_results_sorted_by_similarity():
    chunks = ["a", "b", "c", "d"]
    embeddings = np.array([[1, 0], [0, 1], [0.9, 0.1], [-1, 0]])
    query_embedding = [1, 0]

    results = search_similar_chunks(query_embedding, chunks, embeddings, k=2)

    assert len(results) == 2
    assert results[0]["chunk"] == "a"  # el mas parecido al query
    assert results[0]["similarity"] >= results[1]["similarity"]


def test_save_and_load_index_roundtrip(tmp_path):
    chunks = ["chunk uno", "chunk dos"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    index_path = os.path.join(tmp_path, "index.json")

    save_index(chunks, embeddings, index_path)
    loaded_chunks, loaded_embeddings = load_index(index_path)

    assert loaded_chunks == chunks
    assert loaded_embeddings.tolist() == embeddings


# ---------------------------------------------------------------------------
# query.py — contrato JSON de salida (sin llamar a la API)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    """Indice chico y determinista para no depender de embeddings reales."""
    chunks = ["primer chunk", "segundo chunk", "tercer chunk"]
    embeddings = [[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]]
    index_path = os.path.join(tmp_path, "index.json")
    save_index(chunks, embeddings, index_path)

    monkeypatch.setattr(query, "embed_query", lambda text: [1.0, 0.0])
    monkeypatch.setattr(query, "generate_answer", lambda q, chunks: "respuesta simulada")

    return index_path


def test_answer_question_returns_exact_json_keys(fake_index):
    result = query.answer_question("pregunta de prueba", index_path=fake_index, k=2)
    assert set(result.keys()) == {"user_question", "system_answer", "chunks_related"}


def test_answer_question_respects_k(fake_index):
    result = query.answer_question("pregunta de prueba", index_path=fake_index, k=2)
    assert len(result["chunks_related"]) == 2


def test_answer_question_output_is_json_serializable(fake_index):
    result = query.answer_question("pregunta de prueba", index_path=fake_index, k=2)
    # Si esto no tira excepcion, el JSON de salida es valido de punta a punta.
    json.dumps(result, ensure_ascii=False)
