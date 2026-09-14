"""Experimento: compara zero-shot, few-shot y chain-of-thought sobre el
mismo set de preguntas, midiendo tokens, latencia, costo y precisión.

El prompt que gana esta comparación es el que se copia a
prompts/main_prompt.txt, que es el que usa run_query.py en producción.

Uso:
    python src/compare_prompt_techniques.py
"""

import os

from dotenv import load_dotenv

from llm_client import ask
from metrics import estimate_cost_usd, log_comparison_row, now_iso
from schema import validate_response

COMPARISON_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "metrics", "prompt_comparison.csv"
)

# Las tres variantes "puras" a comparar. Los archivos están en prompts/variants/.
VARIANTS = {
    "zero_shot": os.path.join(
        os.path.dirname(__file__), "..", "prompts", "variants", "zero_shot.txt"
    ),
    "few_shot": os.path.join(
        os.path.dirname(__file__), "..", "prompts", "variants", "few_shot.txt"
    ),
    "chain_of_thought": os.path.join(
        os.path.dirname(__file__), "..", "prompts", "variants", "chain_of_thought.txt"
    ),
}

# Set de preguntas de prueba, una por cada acción del catálogo (ver schema.py)
TEST_QUESTIONS = [
    {
        "question": "¿Cómo cambio la contraseña de mi cuenta?",
        "expected_action": "responder_directamente",
    },
    {
        "question": "Che quiero cancelar",
        "expected_action": "pedir_mas_informacion",
    },
    {
        "question": "La app se cierra sola cada vez que abro la sección de facturación, versión 4.2.1 en Android",
        "expected_action": "crear_ticket_bug",
    },
    {
        "question": "Quiero que me devuelvan la plata del pedido #4521, ya pasaron 20 días y nadie me contesta",
        "expected_action": "escalar_a_humano",
    },
    {
        "question": "Esto ya lo pregunté ayer y me dijeron que lo iban a resolver, es el mismo problema de facturación de siempre",
        "expected_action": "cerrar_ticket_duplicado",
    },
]


def run_comparison(model: str = "gpt-4o-mini") -> list[dict]:
    """Corre cada pregunta de prueba contra cada variante de prompt."""
    rows = []

    for variant_name, prompt_path in VARIANTS.items():
        for case in TEST_QUESTIONS:
            result = ask(case["question"], model=model, system_prompt_path=prompt_path)

            if result["parsed"] is not None:
                errors = validate_response(result["parsed"])
            else:
                errors = [result["parse_error"] or "respuesta vacía o no parseable"]

            valid = len(errors) == 0
            actions_returned = result["parsed"].get("actions", []) if valid else []

            correct = valid and case["expected_action"] in actions_returned

            row = {
                "timestamp": now_iso(),
                "variant": variant_name,
                "question": case["question"],
                "tokens_prompt": result["prompt_tokens"],
                "tokens_completion": result["completion_tokens"],
                "total_tokens": result["total_tokens"],
                "latency_ms": result["latency_ms"],
                "estimated_cost_usd": estimate_cost_usd(
                    model, result["prompt_tokens"], result["completion_tokens"]
                ),
                "valid_json": valid,
                "expected_action": case["expected_action"],
                "actions_returned": ";".join(actions_returned),
                "correct": correct,
            }
            log_comparison_row(COMPARISON_CSV_PATH, row)
            rows.append(row)

    return rows


def summarize(rows: list[dict]) -> None:
    """Imprime una tabla resumen: por cada variante, promedio de tokens,
    latencia, costo, y precisión (accuracy) sobre el set de prueba.
    """
    variants = sorted(set(r["variant"] for r in rows))

    print(
        f"{'variant':<18}{'accuracy':<12}{'avg_tokens':<14}{'avg_latency_ms':<18}{'total_cost_usd':<16}"
    )
    for variant in variants:
        variant_rows = [r for r in rows if r["variant"] == variant]
        n = len(variant_rows)
        accuracy = sum(1 for r in variant_rows if r["correct"]) / n
        avg_tokens = sum(r["total_tokens"] for r in variant_rows) / n
        avg_latency = sum(r["latency_ms"] for r in variant_rows) / n
        total_cost = sum(r["estimated_cost_usd"] for r in variant_rows)
        print(
            f"{variant:<18}{accuracy:<12.0%}{avg_tokens:<14.1f}{avg_latency:<18.1f}{total_cost:<16.6f}"
        )


def main():
    load_dotenv()
    rows = run_comparison()
    summarize(rows)


if __name__ == "__main__":
    main()
