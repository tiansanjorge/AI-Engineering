"""Almacenamiento del indice y busqueda por similitud (k-NN a mano, con NumPy)."""

import json
import os

import numpy as np


def save_index(chunks: list[str], embeddings: list[list[float]], path: str) -> None:
    """Etapa 4 del pipeline de indexacion: guarda chunks + embeddings juntos
    en un archivo JSON (el indice)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    index = {"chunks": chunks, "embeddings": embeddings}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def load_index(path: str) -> tuple[list[str], np.ndarray]:
    """Lee el indice guardado por save_index. Devuelve los chunks y una
    matriz de embeddings (una fila por chunk)."""
    with open(path, "r", encoding="utf-8") as f:
        index = json.load(f)
    return index["chunks"], np.array(index["embeddings"])


def cosine_similarity(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Similitud coseno entre un vector y cada fila de una matriz.

    coseno(a, b) = (a . b) / (|a| * |b|). Se calcula explicito (no se
    delega a una libreria de vector store) para que el metodo de busqueda
    quede auditable en el propio codigo.
    """
    query_norm = query_vector / np.linalg.norm(query_vector)
    matrix_norms = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix_norms @ query_norm


def search_similar_chunks(
    query_embedding: list[float],
    chunks: list[str],
    embeddings: np.ndarray,
    k: int = 3,
) -> list[dict]:
    """Busqueda k-NN: devuelve los k chunks mas similares a la consulta,
    ordenados de mayor a menor similitud coseno."""
    similarities = cosine_similarity(np.array(query_embedding), embeddings)
    top_k_indices = np.argsort(similarities)[::-1][:k]

    return [
        {"chunk": chunks[i], "similarity": round(float(similarities[i]), 4)}
        for i in top_k_indices
    ]
