"""Evaluacion de los resultados del sistema contra el ground truth (`expected.json`).

Mide, para cada corrida, cuatro cosas:
  - cobertura: cuantas de las secciones realmente modificadas se detectaron (recall);
  - falsos positivos: secciones reportadas que NO cambiaron (ruido que costaria tiempo a un abogado);
  - tipo de cambio: adicion / eliminacion / modificacion acertado;
  - hechos clave: cifras y datos que el resumen debe mencionar.

Son metricas deterministas (sin LLM-juez): comparan contra una respuesta correcta escrita de antemano.
"""

import re
import unicodedata

from src.models import ContractChangeOutput, ExtractionResult

ORDINALS = [
    "primera",
    "segunda",
    "tercera",
    "cuarta",
    "quinta",
    "sexta",
    "septima",
    "octava",
    "novena",
    "decima",
]

SectionKey = tuple[str, str]  # (ordinal, inciso)


def section_key(text: str) -> SectionKey:
    """Clave comparable de un identificador de seccion: (ordinal, inciso).

    'Cláusula Cuarta, inciso 4.3' y 'inciso 4.3 de la CLÁUSULA CUARTA' dan la misma clave, asi
    la evaluacion no depende de como redacta el identificador el modelo.
    """
    plain = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    )
    ordinal = next((o for o in ORDINALS if o in plain), "")
    inciso = re.search(r"\d+\.\d+", plain)
    return ordinal, inciso.group(0) if inciso else ""


def _same_section(a: SectionKey, b: SectionKey) -> bool:
    # Mismo ordinal; el inciso solo desempata si ambos lo traen (reportar 'Cláusula Cuarta' a
    # secas cubre al inciso 4.3, pero 'inciso 4.1' NO cubre al 4.3).
    return a[0] == b[0] and (a[1] == b[1] or not a[1] or not b[1])


def evaluate(
    expected: dict,
    output: ContractChangeOutput,
    detail: ExtractionResult | None = None,
) -> dict:
    """Compara una corrida con el ground truth. `detail` aporta los tipos de cambio."""
    exp = [(section_key(c["section"]), c["change_type"]) for c in expected["changes"]]
    if detail is not None:
        reported = [
            (section_key(c.section), c.change_type.value) for c in detail.changes
        ]
    else:
        reported = [(section_key(s), None) for s in output.sections_changed]

    found = [e for e in exp if any(_same_section(e[0], r[0]) for r in reported)]
    type_correct = sum(
        any(_same_section(e[0], r[0]) and r[1] == e[1] for r in reported) for e in found
    )
    extras = [r for r in reported if not any(_same_section(r[0], e[0]) for e in exp)]

    facts = expected["key_facts_in_summary"]
    summary = output.summary_of_the_change
    facts_found = sum(f in summary for f in facts)

    row = {
        "sections_expected": len(exp),
        "sections_found": len(found),
        "type_correct": type_correct if detail is not None else None,
        "false_positives": [" ".join(k).strip() for k, _ in extras],
        "facts_found": facts_found,
        "facts_total": len(facts),
        # El agente 2 cierra el resumen con 'Advertencia:' cuando el mapa detecto inconsistencias.
        "has_warning": "advertencia:" in summary.lower(),
        # Muletilla: el resumen habla del mapa o de las alertas sin que haya una advertencia real.
        "has_filler": "advertencia:" not in summary.lower()
        and bool(re.search(r"alerta|mapa contextual", summary, re.IGNORECASE)),
        "reported_sections": sorted(" ".join(k).strip() for k, _ in reported),
    }
    row["perfect"] = (
        row["sections_found"] == row["sections_expected"]
        and not row["false_positives"]
        and not row["has_filler"]
        and row["facts_found"] == row["facts_total"]
        and (detail is None or row["type_correct"] == row["sections_expected"])
    )
    return row


def aggregate(rows: list[dict]) -> dict:
    """Resumen de varias corridas del MISMO caso: exactitud promedio y estabilidad."""
    n = len(rows)
    typed = [r for r in rows if r["type_correct"] is not None]
    return {
        "runs": n,
        "perfect_runs": sum(r["perfect"] for r in rows),
        "recall": sum(r["sections_found"] for r in rows)
        / sum(r["sections_expected"] for r in rows),
        "type_accuracy": (
            sum(r["type_correct"] for r in typed)
            / sum(r["sections_expected"] for r in typed)
            if typed
            else None
        ),
        "false_positives_total": sum(len(r["false_positives"]) for r in rows),
        "facts_rate": sum(r["facts_found"] for r in rows)
        / sum(r["facts_total"] for r in rows),
        "warning_rate": sum(r["has_warning"] for r in rows) / n,
        "filler_rate": sum(r["has_filler"] for r in rows) / n,
        # Estable = todas las corridas reportaron exactamente el mismo conjunto de secciones.
        "stable": len({tuple(r["reported_sections"]) for r in rows}) == 1,
    }
