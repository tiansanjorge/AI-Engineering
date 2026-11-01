"""Evaluacion de punta a punta con repeticiones: imagen -> parseo -> agentes -> JSON.

Corre el pipeline REAL (el mismo de `main.py`) N veces por par y compara cada resultado con el
ground truth. Repetir importa: un LLM no es determinista, asi que una sola corrida acertada no
prueba nada; "9 de 9" si es una afirmacion defendible.

Todas las corridas comparten un `session_id`, por lo que en Langfuse se ven agrupadas en la
vista de Sesiones. Evidencia en outputs/eval_e2e.json.

Uso (desde modulo-4/):  python scripts/run_eval.py [--runs 3] [--only par1_simple]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.evaluation import aggregate, evaluate
from src.main import analyze_contracts
from src.observability import flush

OUTPUT = config.MODULE_ROOT / "outputs" / "eval_e2e.json"


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--runs", type=int, default=3, help="repeticiones por par")
    cli.add_argument("--only", help="un solo par (nombre de carpeta)")
    args = cli.parse_args()

    config.require_openai_key()
    session_id = f"eval-e2e-{datetime.now():%Y%m%d-%H%M%S}"
    print(f"Sesion de Langfuse: {session_id}\n")

    report = {"session_id": session_id, "runs_per_case": args.runs, "cases": {}}
    for case in sorted(p for p in config.TEST_CONTRACTS_DIR.iterdir() if p.is_dir()):
        if args.only and case.name != args.only:
            continue
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        rows = []
        for i in range(args.runs):
            result = analyze_contracts(
                case / expected["images"]["original"],
                case / expected["images"]["amendment"],
                session_id=session_id,
            )
            row = evaluate(expected, result.output, result.detail)
            row.update(
                latency_s=round(sum(s.latency_s for s in result.stages), 1),
                total_tokens=sum(s.total_tokens for s in result.stages),
                trace_url=result.trace_url,
                output=result.output.model_dump(),
            )
            rows.append(row)
            print(
                f"{case.name:26} corrida {i + 1}: secciones {row['sections_found']}/"
                f"{row['sections_expected']}  tipos {row['type_correct']}  "
                f"falsos+ {len(row['false_positives'])}  hechos {row['facts_found']}/"
                f"{row['facts_total']}  advertencia={'si' if row['has_warning'] else 'no'}  "
                f"{row['latency_s']}s  {row['total_tokens']} tok"
            )
        agg = aggregate(rows)
        report["cases"][case.name] = {"aggregate": agg, "runs": rows}
        print(
            f"  -> {agg['perfect_runs']}/{agg['runs']} corridas perfectas | recall "
            f"{agg['recall']:.0%} | tipos {agg['type_accuracy']:.0%} | falsos+ "
            f"{agg['false_positives_total']} | hechos {agg['facts_rate']:.0%} | "
            f"estable={agg['stable']}\n"
        )

    flush()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Evidencia en {OUTPUT.relative_to(config.MODULE_ROOT)}")


if __name__ == "__main__":
    main()
