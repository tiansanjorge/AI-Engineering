"""Carga del documento fuente y division en chunks de tamano fijo."""

import os


def load_document(path: str) -> str:
    """Lee el documento fuente como texto plano (UTF-8)."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = 100, overlap: int = 20) -> list[str]:
    """Divide el texto en bloques de chunk_size palabras, solapando
    overlap palabras entre bloques consecutivos.

    Tamano fijo con solapamiento: los parametros (chunk_size, overlap)
    quedan documentados aca y en el README. El overlap evita que una
    oracion importante quede cortada a la mitad entre dos chunks
    consecutivos, sin necesidad de detectar limites de oracion.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    words = text.split()
    step = chunk_size - overlap
    chunks = []

    start = 0
    while start < len(words):
        block = words[start : start + chunk_size]
        chunks.append(" ".join(block))
        start += step

    return chunks


def load_and_chunk_document(
    path: str, chunk_size: int = 100, overlap: int = 20
) -> list[str]:
    """Etapas 1 y 2 del pipeline de indexacion: carga el documento y lo
    parte en chunks."""
    text = load_document(path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


DEFAULT_DOCUMENT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "faq_document.txt"
)
