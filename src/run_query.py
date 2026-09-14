"""Entrypoint CLI: recibe una pregunta y devuelve el JSON del asistente.

Uso:
    python src/run_query.py "No puedo iniciar sesión en mi cuenta"
    python src/run_query.py "..." --model gpt-4o-mini
"""

import argparse
import json
import os

from dotenv import load_dotenv

# Se intenta primero el import "de paquete" (from src.xxx import ...), para
# que funcione si alguien hace `from src.run_query import run` (por ejemplo,
# un test futuro) con la raíz del repo en su sys.path. Si eso falla, se cae
# al import "plano", que es el que funciona corriendo este archivo directo
# con `python src/run_query.py` (ahí Python solo agrega src/ al path, no la
# raíz del repo, así que "src.xxx" no se puede resolver).
try:
    from src.llm_client import ask, load_system_prompt
    from src.metrics import estimate_cost_usd, log_execution, now_iso
    from src.safety import detect_adversarial_input, detect_unsafe_output
    from src.schema import fallback_response, validate_response
except ImportError:
    from llm_client import ask, load_system_prompt
    from metrics import estimate_cost_usd, log_execution, now_iso
    from safety import detect_adversarial_input, detect_unsafe_output
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
    """Orquesta un ciclo completo: seguridad de entrada -> modelo ->
    validación de contrato -> seguridad de salida -> métricas -> respuesta.
    """
    # Capa 1 de seguridad: se revisa la pregunta ANTES de gastar una
    # llamada a la API. Si parece un intento de prompt injection, se corta
    # acá — ni se llama al modelo.
    input_safety_errors = detect_adversarial_input(question)
    if input_safety_errors:
        output = fallback_response("entrada bloqueada por seguridad: " + "; ".join(input_safety_errors))
        log_execution(
            METRICS_PATH,
            {
                "timestamp": now_iso(),
                "question": question,
                "model": model,
                "tokens_prompt": 0,
                "tokens_completion": 0,
                "total_tokens": 0,
                "latency_ms": 0.0,
                "estimated_cost_usd": 0.0,
                "valid_json": True,
                "repaired": False,
                "safety_action": "input_blocked",
            },
        )
        return output

    # Acá se hace la llamada real (y paga) a la API de OpenAI.
    result = ask(question, model=model)

    if result["parsed"] is not None:
        # Chequeamos que se cumpla nuestro contrato de negocio
        errors = validate_response(result["parsed"])
    else:
        errors = [result["parse_error"] or "respuesta vacía o no parseable"]

    valid = len(errors) == 0

    output = result["parsed"] if valid else fallback_response("; ".join(errors))

    # Capa 2 de seguridad: se revisa la respuesta final DESPUÉS de tenerla,
    # por si el modelo terminó filtrando algo pese a que la pregunta no
    # disparó la capa 1.
    safety_action = "none"
    if valid:
        output_safety_errors = detect_unsafe_output(output.get("answer", ""), load_system_prompt())
        if output_safety_errors:
            output = fallback_response("salida bloqueada por seguridad: " + "; ".join(output_safety_errors))
            safety_action = "output_blocked"

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
            "safety_action": safety_action,
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
