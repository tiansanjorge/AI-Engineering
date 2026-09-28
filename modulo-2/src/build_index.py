"""Pipeline de indexacion: documento -> chunks -> embeddings -> indice guardado.

Uso:
    python src/build_index.py
    python src/build_index.py --document data/faq_document.txt --chunk-size 150 --overlap 30
"""

import argparse
import os

from dotenv import load_dotenv

from chunking import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_DOCUMENT_PATH,
    DEFAULT_OVERLAP,
    load_and_chunk_document,
)
from embeddings import generate_embeddings
from vector_store import save_index

DEFAULT_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "index.json"
)


def build_index(
    document_path: str = DEFAULT_DOCUMENT_PATH,
    index_path: str = DEFAULT_INDEX_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> None:
    """Corre las 4 etapas del pipeline de indexacion y deja el resultado
    en index_path."""
    chunks = load_and_chunk_document(document_path, chunk_size, overlap)
    print(f"[build_index] {len(chunks)} chunks generados desde {document_path}")

    embeddings = generate_embeddings(chunks)
    print(f"[build_index] {len(embeddings)} embeddings generados")

    save_index(chunks, embeddings, index_path)
    print(f"[build_index] indice guardado en {index_path}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline de indexacion RAG")
    parser.add_argument("--document", default=DEFAULT_DOCUMENT_PATH)
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH)
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="tokens por chunk"
    )
    parser.add_argument(
        "--overlap", type=int, default=DEFAULT_OVERLAP, help="tokens de solapamiento"
    )
    args = parser.parse_args()

    build_index(args.document, args.index, args.chunk_size, args.overlap)


if __name__ == "__main__":
    main()
