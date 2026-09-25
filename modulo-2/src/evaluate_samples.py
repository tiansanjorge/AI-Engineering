"""Corre el agente evaluador sobre outputs/sample_queries.json.

No modifica ese archivo (mantiene el contrato de 3 claves que valida
query.py): guarda el resultado en un archivo separado.

Uso:
    python src/evaluate_samples.py
"""

import json
import os

from dotenv import load_dotenv

from evaluator import evaluate_response

DEFAULT_SAMPLES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "outputs", "sample_queries.json"
)
DEFAULT_OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "outputs", "sample_queries_evaluated.json"
)


def evaluate_samples(
    samples_path: str = DEFAULT_SAMPLES_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> list[dict]:
    """Evalua cada entrada de samples_path y guarda el resultado en output_path."""
    with open(samples_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    evaluated = []
    for sample in samples:
        evaluation = evaluate_response(
            sample["user_question"], sample["system_answer"], sample["chunks_related"]
        )
        evaluated.append({**sample, **evaluation})

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evaluated, f, ensure_ascii=False, indent=2)

    return evaluated


def main() -> None:
    load_dotenv()
    evaluated = evaluate_samples()
    for item in evaluated:
        print(f"[{item['score']}/10] {item['user_question']}")
        print(f"  {item['reason']}\n")


if __name__ == "__main__":
    main()
