"""Entrypoint CLI: recibe una pregunta y devuelve el JSON del asistente.

Uso:
    python src/run_query.py "No puedo iniciar sesión en mi cuenta"
    python src/run_query.py "..." --model gpt-4o-mini
"""

import argparse
import json
import os

from dotenv import load_dotenv
from llm_client import ask
from metrics import estimate_cost_usd, log_execution, now_iso
from schema import fallback_response, validate_response

METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "metrics", "metrics.csv")


def parse_args(argv=None):
    """Define qué argumentos acepta el script por línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Asistente de soporte: pregunta -> JSON (answer, confidence, actions)."
    )
    # Argumento posicional (obligatorio, sin "--"): la pregunta en sí.
    parser.add_argument("question", help="Pregunta o mensaje del cliente/agente")
    # Argumento opcional (con "--"): si no lo pasás, usa el valor default.
    parser.add_argument(
        "--model", default="gpt-4o-mini", help="Modelo a usar (default: gpt-4o-mini)"
    )
    return parser.parse_args(argv)


def run(question: str, model: str) -> dict:
    """Orquesta un ciclo completo: pregunta -> modelo -> validación ->
    métricas -> respuesta final.
    """
    # Acá se hace la llamada real (y paga) a la API de OpenAI.
    result = ask(question, model=model)

    if result["parsed"] is not None:
        # Chequeamos que se cumpla nuestro contrato de negocio
        errors = validate_response(result["parsed"])
    else:
        errors = [result["parse_error"] or "respuesta vacía o no parseable"]

    valid = len(errors) == 0

    output = result["parsed"] if valid else fallback_response("; ".join(errors))

    log_execution(
        METRICS_PATH,
        {
            "timestamp": now_iso(),
            "question": question,
            "model": model,
            "tokens_prompt": result["prompt_tokens"],
            "tokens_completion": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
            "latency_ms": result["latency_ms"],
            "estimated_cost_usd": estimate_cost_usd(
                model, result["prompt_tokens"], result["completion_tokens"]
            ),
            "valid_json": valid,
            "repaired": result["repaired"],
        },
    )

    return output


# Función Principal
def main():
    load_dotenv()
    args = parse_args()
    output = run(args.question, args.model)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
