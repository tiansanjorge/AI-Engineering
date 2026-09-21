"""Capa de integración con la API de OpenAI."""

import json
import os
import time

from openai import OpenAI

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
DEFAULT_PROMPT_PATH = os.path.join(PROMPTS_DIR, "main_prompt.txt")
JSON_REPAIR_INSTRUCTION = (
    "Fix invalid JSON. Output only valid JSON, nothing else. "
    'Required keys: "answer" (string), "confidence" (number 0.0-1.0), '
    '"actions" (non-empty array).'
)


def load_system_prompt(path: str = DEFAULT_PROMPT_PATH) -> str:
    """Lee y devuelve el prompt de sistema desde un archivo de texto."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _try_parse_json(text: str):
    """Intenta convertir un string en formato JSON en un diccionario de Python."""
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, str(e)


def ask(
    question: str,
    model: str = "gpt-4o-mini",
    system_prompt_path: str = DEFAULT_PROMPT_PATH,
) -> dict:
    """Le hace una pregunta al modelo y devuelve el resultado más métricas
    de la llamada (tokens usados, latencia).
    """
    client = OpenAI()
    system_prompt = load_system_prompt(system_prompt_path)

    start = time.perf_counter()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Consulta: {question}"},
        ],
        # 0.4: valor moderado elegido a criterio. Busca respuestas poco erráticas sin volverlas
        # robóticas; su costo es ruido entre corridas (ver "Trade-offs" del reporte).
        temperature=0.4,
        # 500: techo de seguridad contra respuestas desbordadas.
        # Lo medido en metrics/*.csv no pasa de ~160 tokens
        # de completion (máx. 114 en el experimento), o sea >3x de margen.
        max_completion_tokens=500,
        response_format={"type": "json_object"},
    )

    raw_content = completion.choices[0].message.content or ""

    usage = completion.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens

    parsed, parse_error = _try_parse_json(raw_content)

    repaired = False

    # Reparación de JSON con una segunda llamada determinista (temperature=0)
    if parsed is None:
        repaired = True
        repair_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": JSON_REPAIR_INSTRUCTION},
                {"role": "user", "content": raw_content},
            ],
            temperature=0,
            max_completion_tokens=500,
            response_format={"type": "json_object"},
        )
        raw_content = repair_completion.choices[0].message.content or raw_content
        repair_usage = repair_completion.usage
        prompt_tokens += repair_usage.prompt_tokens
        completion_tokens += repair_usage.completion_tokens
        parsed, parse_error = _try_parse_json(raw_content)

    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "parsed": parsed,
        "parse_error": parse_error,
        "raw_content": raw_content,
        "repaired": repaired,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "latency_ms": latency_ms,
        "system_prompt": system_prompt,
    }
