"""Evaluacion de punta a punta con repeticiones: imagen -> parseo -> agentes -> JSON.

Corre el pipeline REAL (el mismo de `main.py`) N veces por par y compara cada resultado con el
ground truth. Repetir importa: un LLM no es determinista, asi que una sola corrida acertada no
prueba nada; "9 de 9" si es una afirmacion defendible.

Todas las corridas comparten un `session_id`, por lo que en Langfuse se ven agrupadas en la
vista de Sesiones. Evidencia en outputs/eval_e2e.json.

Uso (desde modulo-4/):  python scripts/run_eval.py [--runs 3] [--only par4_ciego par5_inyeccion] [--output ruta.json]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.errors import ContractAnalysisError
from src.evaluation import aggregate, evaluate
from src.main import analyze_contracts
from src.observability import flush

OUTPUT = config.MODULE_ROOT / "outputs" / "eval_e2e.json"


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--runs", type=int, default=3, help="repeticiones por par")
    cli.add_argument("--only", nargs="+", help="uno o mas pares (nombres de carpeta)")
    cli.add_argument(
        "--output",
        help="archivo de evidencia (default: outputs/eval_e2e.json); permite no pisar "
        "la evidencia de otra version del prompt",
    )
    args = cli.parse_args()
    output = Path(args.output) if args.output else OUTPUT

    config.require_openai_key()
    session_id = f"eval-e2e-{datetime.now():%Y%m%d-%H%M%S}"
    print(f"Sesion de Langfuse: {session_id}\n")

    cases = sorted(p for p in config.TEST_CONTRACTS_DIR.iterdir() if p.is_dir())
    if args.only:
        unknown = set(args.only) - {c.name for c in cases}
        if unknown:
            sys.exit(f"--only: no existe(n) {sorted(unknown)} en data/test_contracts/")
        cases = [c for c in cases if c.name in args.only]

    report = {"session_id": session_id, "runs_per_case": args.runs, "cases": {}}
    try:
        run_cases(cases, args, session_id, report)
    finally:
        # La evidencia se guarda SIEMPRE, tambien ante un fallo a mitad de camino: cada corrida
        # cuesta dinero y no debe perderse por un error en la siguiente.
        flush()
        output.parent.mkdir(exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Evidencia en {output}")


def run_cases(cases, args, session_id: str, report: dict) -> None:
    for case in cases:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        rows = []
        report["cases"][case.name] = {
            "runs": rows
        }  # visible desde el inicio (evidencia parcial)
        for i in range(args.runs):
            try:
                result = analyze_contracts(
                    case / expected["images"]["original"],
                    case / expected["images"]["amendment"],
                    session_id=session_id,
                )
            except ContractAnalysisError as exc:
                # Una corrida fallida se registra y se sigue: tambien es un dato de la evaluacion.
                rows.append({"error": f"{type(exc).__name__}: {exc}"})
                print(
                    f"{case.name:26} corrida {i + 1}: ERROR {type(exc).__name__}: {exc}"
                )
                continue
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
        ok_rows = [r for r in rows if "error" not in r]
        if not ok_rows:
            print(f"  -> {case.name}: ninguna corrida termino bien\n")
            continue
        agg = aggregate(ok_rows)
        agg["failed_runs"] = len(rows) - len(ok_rows)
        report["cases"][case.name]["aggregate"] = agg
        print(
            f"  -> {agg['perfect_runs']}/{args.runs} corridas perfectas "
            f"({agg['failed_runs']} con error) | recall {agg['recall']:.0%} | tipos "
            f"{agg['type_accuracy']:.0%} | falsos+ {agg['false_positives_total']} | hechos "
            f"{agg['facts_rate']:.0%} | muletilla {agg['filler_rate']:.0%} | "
            f"estable={agg['stable']}"
            + (
                f" | inyeccion senalada {agg['injection_flag_rate']:.0%}"
                if "injection_flag_rate" in agg
                else ""
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
