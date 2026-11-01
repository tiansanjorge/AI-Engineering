"""Prueba de estres del parser: lo enfrenta a escaneos cada vez peores y mide donde falla.

Toma las dos adendas (la simple y la compleja), las degrada en 5 niveles de severidad (ver
`generate_contracts.SEVERITIES`), las transcribe con el parser real y mide WER y cuantos datos
clave (cifras, fechas) sobreviven. Sirve para ubicar el punto de quiebre y elegir la dificultad
del par 3. Las imagenes quedan en data/stress_scans/ para poder verlas.

Uso (desde modulo-4/):  python scripts/stress_parsing.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract_specs as specs
import generate_contracts as gen

from src import config
from src.image_parser import parse_contract_image
from src.text_metrics import word_error_rate

OUT_DIR = config.MODULE_ROOT / "data" / "stress_scans"
OUTPUT = config.MODULE_ROOT / "outputs" / "parsing_stress.json"
# (nombre, bloques del documento, datos clave que contiene)
DOCS = [
    ("par1_adenda", specs.SIMPLE_AMENDMENT, ["2026", "2.800"]),
    ("par2_adenda", specs.COMPLEX_AMENDMENT, ["Chile", "Brasil", "4.3", "25.326"]),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for severity in gen.SEVERITIES:
        for name, blocks, facts in DOCS:
            path = OUT_DIR / f"nivel{severity}_{name}.jpg"
            gen.save_scan(gen.degrade(gen.render(blocks), severity), path, severity)
            reference = "\n".join(text for _, text in blocks)
            text = parse_contract_image(path)
            row = {
                "severity": severity,
                "document": name,
                "wer": round(word_error_rate(reference, text), 4),
                "key_facts_found": f"{sum(f in text for f in facts)}/{len(facts)}",
                "image": str(path.relative_to(config.MODULE_ROOT)),
            }
            results.append(row)
            print(
                f"nivel {severity}  {name:12} WER={row['wer']:.3f}  hechos={row['key_facts_found']}"
            )
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
