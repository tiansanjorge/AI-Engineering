"""Tests del pipeline de chunking, busqueda vectorial y consulta.

Ninguno llama a la API real: embed_query y generate_answer se mockean
con monkeypatch, igual que en el Modulo 1. Corren rapido, gratis, y sin
necesitar OPENAI_API_KEY configurada.
"""

import json
import os

import numpy as np
import pytest
import tiktoken

import query
from chunking import (
    DEFAULT_DOCUMENT_PATH,
    chunk_text,
    load_and_chunk_document,
    load_document,
)
from evaluator import build_evaluation_prompt, evaluate_response
from vector_store import cosine_similarity, load_index, save_index, search_similar_chunks

ENCODING = tiktoken.get_encoding("cl100k_base")


# ---------------------------------------------------------------------------
# chunking.py
# ---------------------------------------------------------------------------

def test_chunk_text_respects_chunk_size():
    text = " ".join(f"palabra{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    # el primer chunk tiene exactamente chunk_size tokens (hay suficiente
    # texto); ningun chunk supera ese tamano.
    assert len(ENCODING.encode(chunks[0])) == 100
    assert all(len(ENCODING.encode(chunk)) <= 100 for chunk in chunks)


def test_chunk_text_overlaps_between_consecutive_chunks():
    text = " ".join(f"palabra{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    # los ultimos 20 tokens del primer chunk son los primeros 20 del segundo
    assert (
        ENCODING.encode(chunks[0])[-20:] == ENCODING.encode(chunks[1])[:20]
    )


def test_chunk_text_does_not_emit_tail_contained_in_previous_chunk():
    # 270 tokens con chunk_size=150 y overlap=30: la tercera ventana
    # empezaria en el token 240 y solo tendria 30 tokens, todos ya
    # incluidos en el chunk anterior.
    full = ENCODING.encode(load_document(DEFAULT_DOCUMENT_PATH))
    chunks = chunk_text(ENCODING.decode(full[:270]), chunk_size=150, overlap=30)
    assert len(chunks) == 2


def test_chunk_text_does_not_split_multibyte_characters():
    text = "áéíóú ñ 😀 ü ¿cómo está? " * 200
    chunks = chunk_text(text, chunk_size=150, overlap=30)
    assert len(chunks) > 1
    assert all("�" not in chunk for chunk in chunks)


def test_chunk_text_rejects_overlap_gte_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("cualquier texto", chunk_size=50, overlap=50)


def test_load_and_chunk_document_generates_at_least_20_chunks():
    # Corre contra el documento fuente real (data/faq_document.txt), no
    # un texto sintetico: es la verificacion de que el documento entregado
    # efectivamente cumple el minimo que pide la consigna.
    chunks = load_and_chunk_document(DEFAULT_DOCUMENT_PATH)
    assert len(chunks) >= 20


def test_load_and_chunk_document_chunk_sizes_within_token_range():
    # Tokens reales (cl100k_base, el de text-embedding-3-small), no una
    # estimacion. La consigna pide 50-500 tokens por chunk.
    chunks = load_and_chunk_document(DEFAULT_DOCUMENT_PATH)
    for chunk in chunks:
        assert 50 <= len(ENCODING.encode(chunk)) <= 500


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


# ---------------------------------------------------------------------------
# evaluator.py (bonus) — LLM mockeado, no llama a la API
# ---------------------------------------------------------------------------

def test_build_evaluation_prompt_includes_question_answer_and_chunks():
    prompt = build_evaluation_prompt("pregunta?", "respuesta.", ["chunk uno", "chunk dos"])
    assert "pregunta?" in prompt
    assert "respuesta." in prompt
    assert "chunk uno" in prompt
    assert "chunk dos" in prompt


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_evaluate_response_parses_score_and_reason(monkeypatch):
    fake_json = json.dumps(
        {"score": 8, "reason": "Usa el chunk correcto y responde completo, sin inventar nada fuera del contexto dado."}
    )

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeCompletion(fake_json)

    monkeypatch.setattr("evaluator.OpenAI", lambda: _FakeClient())

    result = evaluate_response("pregunta?", "respuesta.", ["chunk uno"])

    assert result["score"] == 8
    assert len(result["reason"]) >= 50
