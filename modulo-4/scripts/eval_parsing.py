"""Mide la fidelidad del parsing de vision contra el ground truth de cada par.

Para cada imagen: transcribe con `parse_contract_image`, compara con el texto exacto que se
renderizo (`expected.json`) y reporta WER, similitud de caracteres y si cada dato clave
(cifras, fechas) aparece textualmente. Deja la evidencia en outputs/parsing_eval.json.

Uso (desde modulo-4/):  python scripts/eval_parsing.py [--only par1_simple]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.image_parser import parse_contract_image
from src.text_metrics import char_similarity, word_error_rate

OUTPUT = config.MODULE_ROOT / "outputs" / "parsing_eval.json"


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--only", help="nombre de un par (carpeta de data/test_contracts)")
    args = cli.parse_args()

    results = []
    for case in sorted(p for p in config.TEST_CONTRACTS_DIR.iterdir() if p.is_dir()):
        if args.only and case.name != args.only:
            continue
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        for side in ("original", "amendment"):
            image = case / expected["images"][side]
            reference = expected["documents"][side]
            text = parse_contract_image(image)
            # Datos clave del ground truth que viven en este documento (p. ej. montos y fechas).
            facts = [f for f in expected["key_facts_in_summary"] if f in reference]
            row = {
                "case": case.name,
                "document": side,
                "wer": round(word_error_rate(reference, text), 4),
                "char_similarity": round(char_similarity(reference, text), 4),
                "key_facts_found": f"{sum(f in text for f in facts)}/{len(facts)}",
                "transcription": text,
            }
            results.append(row)
            print(
                f"{case.name:26} {side:9} WER={row['wer']:.3f}  "
                f"sim={row['char_similarity']:.3f}  hechos={row['key_facts_found']}"
            )

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEvidencia en {OUTPUT.relative_to(config.MODULE_ROOT)}")


if __name__ == "__main__":
    main()
