"""Construye las colecciones Chroma (una por dominio) desde data/.

Uso (desde modulo-3/):
    python scripts/build_index.py                 # los tres dominios
    python scripts/build_index.py --domain hr     # uno solo
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    CHROMA_DIR,
    DOMAINS,
    EMBEDDING_MODEL,
    EMBEDDING_PRICE_PER_M_TOKENS,
    MAX_CHUNK_TOKENS,
)
from src.ingestion import load_domain
from src.vector_store import build_domain_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa los documentos en Chroma")
    parser.add_argument("--domain", choices=sorted(DOMAINS), help="Un solo dominio")
    args = parser.parse_args()

    total_tokens = 0
    for domain in [args.domain] if args.domain else sorted(DOMAINS):
        documents = load_domain(domain)
        tokens = [d.metadata["tokens"] for d in documents]
        total_tokens += sum(tokens)
        store = build_domain_store(domain)
        print(
            f"[build_index] {domain:8} {len(documents):3} chunks "
            f"(tokens min/max {min(tokens)}/{max(tokens)}, tope {MAX_CHUNK_TOKENS}) "
            f"-> coleccion '{store._collection.name}' ({store._collection.count()} registros)"
        )
    price = EMBEDDING_PRICE_PER_M_TOKENS.get(EMBEDDING_MODEL, 0.0)
    print(
        f"[build_index] {total_tokens} tokens embebidos con {EMBEDDING_MODEL} "
        f"~ USD {total_tokens / 1_000_000 * price:.5f}  (indice en {CHROMA_DIR})"
    )


if __name__ == "__main__":
    main()
