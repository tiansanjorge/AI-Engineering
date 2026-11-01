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
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.models import ExtractionResult

OUTPUT = config.MODULE_ROOT / "outputs" / "agents_eval.json"
ORDINALS = (
    ["primera", "segunda", "tercera", "cuarta", "quinta", "sexta", "septima", "octava", "novena", "decima"]
)


def section_key(text: str) -> tuple[str, str]:
    """Clave comparable de un identificador de seccion: (ordinal, inciso).

    'Cláusula Cuarta, inciso 4.3' y 'inciso 4.3 de la CLÁUSULA CUARTA' dan la misma clave.
    """
    plain = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    )
    ordinal = next((o for o in ORDINALS if o in plain), "")
    inciso = re.search(r"\d+\.\d+", plain)
    return ordinal, inciso.group(0) if inciso else ""


def evaluate(expected: dict, result: ExtractionResult) -> dict:
    exp = {section_key(c["section"]): c["change_type"] for c in expected["changes"]}
    got = {section_key(c.section): c.change_type.value for c in result.changes}
    unchanged = {section_key(s) for s in expected["unchanged_sections"]}
    # Un cambio sobre el inciso 4.3 cuenta aunque la clave del modelo omita el inciso.
    matched = {k for k in exp if k in got or (k[0], "") in got}
    false_pos = [k for k in got if k[0] in {u[0] for u in unchanged} and k not in exp]
    summary = result.summary_of_the_change
    return {
        "sections_expected": len(exp),
        "sections_found": len(matched),
        "change_type_correct": sum(
            got.get(k, got.get((k[0], ""))) == exp[k] for k in matched
        ),
        "false_positives": [f"{o} {i}".strip() for o, i in false_pos],
        "key_facts_in_summary": f"{sum(f in summary for f in expected['key_facts_in_summary'])}"
        f"/{len(expected['key_facts_in_summary'])}",
    }


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
        row = {"case": case.name, **evaluate(expected, result)}
        row["output"] = result.to_output().model_dump()
        row["context_map"] = context_map
        report.append(row)
        print(
            f"{case.name:26} secciones {row['sections_found']}/{row['sections_expected']}  "
            f"tipo ok {row['change_type_correct']}  falsos+ {row['false_positives'] or 0}  "
            f"hechos {row['key_facts_in_summary']}"
        )

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEvidencia en {OUTPUT.relative_to(config.MODULE_ROOT)}")


if __name__ == "__main__":
    main()
