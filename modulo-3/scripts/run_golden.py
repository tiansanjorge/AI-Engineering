"""Corre el golden set completo contra el sistema, trazando cada consulta en Langfuse.

Cada corrida lleva un tag (`golden-run-v1`, `golden-run-v2`, ...) que permite filtrar y comparar
versiones en la UI. Guarda el detalle por caso en eval/golden_runs/<tag>.json y agrega una fila
con las metricas agregadas a eval/golden_summary.csv (historial auditable de las iteraciones).

Uso (desde modulo-3/):
    python scripts/run_golden.py --run-tag golden-run-v1 [--note "descripcion del cambio"]
"""

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.callbacks import get_usage_metadata_callback

from src.config import CHAT_MODEL, MODULE_ROOT
from src.evaluation import (
    BLIND_PATH,
    GOLDEN_PATH,
    HOLDOUT_PATH,
    aggregate,
    evaluate_case,
    load_golden,
)
from src.evaluator import evaluate_trace
from src.observability import flush, traced_query

RUNS_DIR = MODULE_ROOT / "eval" / "golden_runs"
SUMMARY_CSV = MODULE_ROOT / "eval" / "golden_summary.csv"
SUMMARY_FIELDS = [
    "run_tag", "set", "timestamp", "note", "n", "pass_rate", "routing_strict", "routing_lenient",
    "status_ok", "facts_ok", "sources_ok", "forbidden_ok", "false_abstentions", "false_answers",
    "latency_ms_p50", "latency_ms_p95", "input_tokens", "output_tokens", "estimated_cost_usd",
    "scored", "mean_quality", "low_quality_count", "judge_cost_usd",
]  # fmt: skip


def append_summary(row: dict) -> None:
    """Agrega una fila al historial; si el esquema de columnas crecio, migra las filas viejas."""
    rows = []
    if SUMMARY_CSV.exists():
        with SUMMARY_CSV.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    rows.append(row)
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore", restval=""
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corre el golden set y registra las metricas"
    )
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument(
        "--set", choices=["dev", "holdout", "blind"], default="dev",
        help="dev = test_queries.json (se usa para ajustar); holdout = validacion; blind = ciego (se corre sin ajustar nada despues)",
    )  # fmt: skip
    parser.add_argument("--only", nargs="*", help="Ids de casos a correr (diagnostico)")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Puntuar cada respuesta con el evaluador (Langfuse Score API)",
    )
    args = parser.parse_args()

    path = {"dev": GOLDEN_PATH, "holdout": HOLDOUT_PATH, "blind": BLIND_PATH}[args.set]
    cases = [c for c in load_golden(path) if not args.only or c["id"] in args.only]
    evals = []
    for case in cases:
        start = time.perf_counter()
        with get_usage_metadata_callback() as usage:
            traced = traced_query(
                case["query"],
                user_id="golden-runner",
                session_id=args.run_tag,
                tags=[args.run_tag, case["expected_intent"], case["category"]],
                metadata={"case_id": case["id"], "category": case["category"]},
                expected_intent=case["expected_intent"],
            )
        ev = evaluate_case(case, traced.result)
        ev.latency_ms = round((time.perf_counter() - start) * 1000, 1)
        ev.input_tokens = sum(u["input_tokens"] for u in usage.usage_metadata.values())
        ev.output_tokens = sum(
            u["output_tokens"] for u in usage.usage_metadata.values()
        )
        ev.trace_id = traced.trace_id
        if args.judge:
            with get_usage_metadata_callback() as judge_usage:
                verdict = evaluate_trace(traced.trace_id, traced.result)
            if verdict is not None:
                ev.quality_score, ev.quality_reason = verdict.score, verdict.reason
            ev.judge_input_tokens = sum(
                u["input_tokens"] for u in judge_usage.usage_metadata.values()
            )
            ev.judge_output_tokens = sum(
                u["output_tokens"] for u in judge_usage.usage_metadata.values()
            )
        # Score por caso en el mismo trace: filtrable en Langfuse (casos fallidos de esta corrida).
        from langfuse import get_client

        get_client().create_score(
            trace_id=traced.trace_id, name="case_passed", value=float(ev.passed),
            data_type="BOOLEAN", comment=f"{args.run_tag} {case['id']}",
        )  # fmt: skip
        evals.append(ev)
        mark = "PASS" if ev.passed else "FAIL"
        print(f"{mark} {ev.id:8} esperado={ev.expected_intent:12} ruteo={ev.routed_intent!s:12} "
              f"estado={ev.status:12} {ev.latency_ms:7.0f} ms")  # fmt: skip
    flush()

    summary = aggregate(evals)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{args.run_tag}.json").write_text(
        json.dumps(
            {"run_tag": args.run_tag, "model": CHAT_MODEL, "note": args.note, "summary": summary,
             "cases": [e.model_dump() for e in evals]},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )  # fmt: skip
    append_summary(
        {"run_tag": args.run_tag, "set": args.set, "note": args.note,
         "timestamp": datetime.now(UTC).isoformat(), **summary}
    )  # fmt: skip

    print(
        f"\n== {args.run_tag}: {summary['pass_rate']:.0%} de casos OK ({summary['n']} casos) =="
    )
    for key in ("routing_strict", "routing_lenient", "status_ok", "facts_ok", "sources_ok",
                "forbidden_ok", "false_abstentions", "false_answers", "latency_ms_p50",
                "latency_ms_p95", "estimated_cost_usd"):  # fmt: skip
        print(f"  {key:20} {summary[key]}")
    if args.judge:
        print(f"  calidad (juez)       media {summary['mean_quality']}  < 7: "
              f"{summary['low_quality_count']}  costo del juez USD {summary['judge_cost_usd']}")  # fmt: skip
    print("  confusion_matrix    ", json.dumps(summary["confusion_matrix"]))
    for ev in evals:
        if not ev.passed:
            print(f"  FALLA {ev.id}: ruteo={ev.routed_intent} estado={ev.status} facts={ev.facts_ok} "
                  f"fuentes={ev.sources_ok} citadas={ev.cited_sections}")  # fmt: skip


if __name__ == "__main__":
    main()
