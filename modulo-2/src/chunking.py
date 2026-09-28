"""Carga del documento fuente y division en chunks de tamano fijo (en tokens)."""

import os

import tiktoken


# Mismo tokenizador que usa text-embedding-3-small.
_ENCODING = tiktoken.get_encoding("cl100k_base")

DEFAULT_CHUNK_SIZE = 150
DEFAULT_OVERLAP = 30


def load_document(path: str) -> str:
    """Lee el documento fuente como texto plano (UTF-8)."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _is_continuation(token: int) -> bool:
    """True si el token empieza con un byte de continuacion UTF-8, es decir,
    si cortar justo antes de el partiria un caracter multibyte."""
    return _ENCODING.decode_single_token_bytes(token)[0] & 0b11000000 == 0b10000000


def chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    """Divide el texto en bloques de chunk_size tokens, solapando
    overlap tokens entre bloques consecutivos.

    Los bordes se corren unos pocos tokens si hace falta para no partir un
    caracter multibyte (acentos, emojis), asi que un chunk puede exceder
    chunk_size en esos tokens.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    tokens = _ENCODING.encode(text)
    step = chunk_size - overlap
    chunks = []

    start = 0
    while start < len(tokens):
        block_start = start
        while block_start > 0 and _is_continuation(tokens[block_start]):
            block_start -= 1
        end = start + chunk_size
        while end < len(tokens) and _is_continuation(tokens[end]):
            end += 1
        chunks.append(_ENCODING.decode(tokens[block_start:end]))
        if end >= len(tokens):
            break
        start += step

    return chunks


def load_and_chunk_document(
    path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    """Etapas 1 y 2 del pipeline de indexacion: carga el documento y lo
    parte en chunks."""
    text = load_document(path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


DEFAULT_DOCUMENT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "faq_document.txt"
)
