"""Evalua la recuperacion de cada coleccion con un set de preguntas parafraseadas.

Metricas por dominio y globales: hit@1, hit@3, hit@k y MRR (la fuente esperada se identifica por
el nombre de la seccion del chunk). Ademas calcula una linea base de ruteo SIN LLM: asignar cada
pregunta a la coleccion cuyo mejor chunk tiene mayor similitud coseno. Sirve de referencia para
medir cuanto aporta el orquestador (Fase 4/6).

Uso (desde modulo-3/):  python scripts/eval_retrieval.py [--k 4]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DOMAINS, MODULE_ROOT
from src.vector_store import get_store

CASES_PATH = MODULE_ROOT / "eval" / "retrieval_cases.json"
OUTPUT_PATH = MODULE_ROOT / "eval" / "retrieval_results.json"


def evaluate(k: int) -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    stores = {d: get_store(d) for d in DOMAINS}
    rows = []
    for case in cases:
        results = stores[case["domain"]].similarity_search_with_score(
            case["query"], k=k
        )
        sections = [doc.metadata["section"] for doc, _ in results]
        rank = next(
            (i + 1 for i, s in enumerate(sections) if s in case["expected_sections"]),
            None,
        )
        # Distancia coseno de Chroma: menor = mas parecido. Mejor chunk por coleccion:
        best = {
            d: store.similarity_search_with_score(case["query"], k=1)[0][1]
            for d, store in stores.items()
        }
        rows.append(
            {
                "id": case["id"],
                "domain": case["domain"],
                "query": case["query"],
                "rank_of_expected": rank,
                "top_sections": sections,
                "best_distance_by_domain": {d: round(v, 4) for d, v in best.items()},
                "score_based_route": min(best, key=best.get),
            }
        )

    def summarize(subset: list[dict]) -> dict:
        n = len(subset)
        ranks = [r["rank_of_expected"] for r in subset]
        return {
            "n": n,
            "hit@1": sum(r == 1 for r in ranks) / n,
            "hit@3": sum(r is not None and r <= 3 for r in ranks) / n,
            f"hit@{k}": sum(r is not None for r in ranks) / n,
            "mrr": round(sum(1 / r for r in ranks if r) / n, 3),
            "routing_by_best_score": sum(
                r["score_based_route"] == r["domain"] for r in subset
            )
            / n,
        }

    return {
        "k": k,
        "overall": summarize(rows),
        "by_domain": {
            d: summarize([r for r in rows if r["domain"] == d]) for d in DOMAINS
        },
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    report = evaluate(args.k)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"overall": report["overall"], "by_domain": report["by_domain"]}, indent=2
        )
    )
    misses = [c for c in report["cases"] if c["rank_of_expected"] is None]
    for c in misses:
        print(f"[MISS] {c['id']}: {c['query']} -> {c['top_sections']}")
    wrong = [c for c in report["cases"] if c["score_based_route"] != c["domain"]]
    for c in wrong:
        print(
            f"[ROUTE] {c['id']} esperado={c['domain']} por-score={c['score_based_route']} {c['best_distance_by_domain']}"
        )


if __name__ == "__main__":
    main()
