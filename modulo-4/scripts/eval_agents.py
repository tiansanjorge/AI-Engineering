"""Mide la calidad de los dos agentes contra el ground truth de cada par.

Por defecto los alimenta con el texto EXACTO de los documentos (aisla la calidad de los agentes,
sin mezclar errores de lectura). Con --parsed usa en cambio las transcripciones reales de
outputs/parsing_eval.json (el camino completo, con los errores del parser incluidos).

Metricas por par: secciones detectadas vs esperadas (recall / falsos positivos), tipo de cambio
acertado y datos clave presentes en el resumen. Evidencia en outputs/agents_eval.json.

Uso (desde modulo-4/):  python scripts/eval_agents.py [--parsed] [--only par2_complejo]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.evaluation import evaluate

OUTPUT = config.MODULE_ROOT / "outputs" / "agents_eval.json"


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument(
        "--parsed", action="store_true", help="usar transcripciones reales"
    )
    cli.add_argument("--only")
    args = cli.parse_args()

    parsed = {}
    if args.parsed:
        for row in json.loads(
            (config.MODULE_ROOT / "outputs" / "parsing_eval.json").read_text("utf-8")
        ):
            parsed[(row["case"], row["document"])] = row["transcription"]

    ctx_agent, ext_agent = ContextualizationAgent(), ExtractionAgent()
    report = []
    for case in sorted(p for p in config.TEST_CONTRACTS_DIR.iterdir() if p.is_dir()):
        if args.only and case.name != args.only:
            continue
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        original = (
            parsed.get((case.name, "original")) or expected["documents"]["original"]
        )
        amendment = (
            parsed.get((case.name, "amendment")) or expected["documents"]["amendment"]
        )

        context_map = ctx_agent.run(original, amendment)
        result = ext_agent.extract(context_map, original, amendment)
        row = {"case": case.name, **evaluate(expected, result.to_output(), result)}
        row["output"] = result.to_output().model_dump()
        row["context_map"] = context_map
        report.append(row)
        print(
            f"{case.name:26} secciones {row['sections_found']}/{row['sections_expected']}  "
            f"tipo ok {row['type_correct']}  falsos+ {row['false_positives'] or 0}  "
            f"hechos {row['facts_found']}/{row['facts_total']}"
        )

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEvidencia en {OUTPUT.relative_to(config.MODULE_ROOT)}")


if __name__ == "__main__":
    main()
