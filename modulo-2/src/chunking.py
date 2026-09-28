"""Carga del documento fuente y division en chunks de tamano fijo (en tokens)."""

import os

import tiktoken


# Mismo tokenizador que usa text-embedding-3-small.
_ENCODING = tiktoken.get_encoding("cl100k_base")


def load_document(path: str) -> str:
    """Lee el documento fuente como texto plano (UTF-8)."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = 150, overlap: int = 30) -> list[str]:
    """Divide el texto en bloques de chunk_size tokens, solapando
    overlap tokens entre bloques consecutivos.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    tokens = _ENCODING.encode(text)
    step = chunk_size - overlap
    chunks = []

    start = 0
    while start < len(tokens):
        block = tokens[start : start + chunk_size]
        chunks.append(_ENCODING.decode(block))
        start += step

    return chunks


def load_and_chunk_document(
    path: str, chunk_size: int = 150, overlap: int = 30
) -> list[str]:
    """Etapas 1 y 2 del pipeline de indexacion: carga el documento y lo
    parte en chunks."""
    text = load_document(path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


DEFAULT_DOCUMENT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "faq_document.txt"
)
