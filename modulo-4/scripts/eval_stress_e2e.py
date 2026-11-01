"""Que hace el sistema COMPLETO cuando la adenda llega muy degradada (niveles 3 y 4).

Cierra la pregunta abierta de PENDIENTES.md (P-04/P-06): con escaneos malos el parser puede leer
mal o inventar datos. Aca se mide si el sistema, de punta a punta, lo detecta (advertencia en el
resumen), lo propaga sin avisar (valor falso presentado como real) o se frena con un error.

Usa el original limpio del par 1 y la adenda degradada de `data/stress_scans/`. Repite cada nivel
para ver la estabilidad. Evidencia en outputs/stress_e2e.json.

Uso (desde modulo-4/):  python scripts/eval_stress_e2e.py [--runs 3]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.errors import ContractAnalysisError
from src.main import analyze_contracts
from src.observability import flush

OUTPUT = config.MODULE_ROOT / "outputs" / "stress_e2e.json"
CASE = config.TEST_CONTRACTS_DIR / "par1_simple"
# Valores correctos de la adenda: si el resumen contiene OTROS, se propago un dato falso.
CORRECT = ["2026", "2.800"]


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--runs", type=int, default=3)
    args = cli.parse_args()
    config.require_openai_key()

    report = {}
    for level in (3, 4):
        amendment = (
            config.MODULE_ROOT
            / "data"
            / "stress_scans"
            / f"nivel{level}_par1_adenda.jpg"
        )
        rows = []
        for i in range(args.runs):
            row = {"run": i + 1}
            try:
                result = analyze_contracts(
                    CASE / "original.png",
                    amendment,
                    session_id=f"stress-e2e-nivel{level}",
                )
                summary = result.output.summary_of_the_change
                row.update(
                    outcome="resultado",
                    has_warning="advertencia:" in summary.lower(),
                    correct_facts=sum(f in summary for f in CORRECT),
                    summary=summary,
                )
            except ContractAnalysisError as exc:
                # Frenarse con un error claro tambien es un comportamiento seguro.
                row.update(outcome=f"error:{type(exc).__name__}", detail=str(exc)[:200])
            rows.append(row)
            print(
                f"nivel {level} corrida {i + 1}: {row['outcome']}"
                + (
                    f"  advertencia={'si' if row['has_warning'] else 'NO'}  "
                    f"hechos correctos {row['correct_facts']}/{len(CORRECT)}"
                    if row["outcome"] == "resultado"
                    else ""
                )
            )
        report[f"nivel{level}"] = rows

    flush()
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEvidencia en {OUTPUT.relative_to(config.MODULE_ROOT)}")


if __name__ == "__main__":
    main()
