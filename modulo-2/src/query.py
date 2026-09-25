"""Pipeline de consulta: pregunta -> embedding -> busqueda -> respuesta -> JSON.

Uso:
    python src/query.py "Cuantos dias de PTO acumulo por mes?"
    python src/query.py "..." --k 5
"""

import argparse
import json
import os

from dotenv import load_dotenv

from embeddings import embed_query
from llm_client import generate_answer
from vector_store import load_index, search_similar_chunks

DEFAULT_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "index.json"
)


def answer_question(question: str, index_path: str = DEFAULT_INDEX_PATH, k: int = 3) -> dict:
    """Corre las 4 etapas del pipeline de consulta y devuelve el JSON de
    salida con las 3 claves que exige la consigna."""
    chunks, embeddings = load_index(index_path)

    query_embedding = embed_query(question)
    results = search_similar_chunks(query_embedding, chunks, embeddings, k=k)
    chunks_related = [r["chunk"] for r in results]

    system_answer = generate_answer(question, chunks_related)

    return {
        "user_question": question,
        "system_answer": system_answer,
        "chunks_related": chunks_related,
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pipeline de consulta RAG")
    parser.add_argument("question")
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    result = answer_question(args.question, args.index, args.k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
