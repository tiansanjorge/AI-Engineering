"""Cálculo de costo y registro de métricas por ejecución."""

import csv
import json
import os
from datetime import datetime, timezone

# Ruta al archivo de precios (no lo carga todavía, solo arma la ruta).
PRICING_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "pricing.json"
)


def load_pricing(path: str = PRICING_CONFIG_PATH) -> dict:
    """Lee la tabla de precios desde config/pricing.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


PRICING_PER_MILLION_TOKENS = load_pricing()


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calcula cuánto costó (en dólares) una llamada al modelo."""

    pricing = PRICING_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        return 0.0

    cost = (prompt_tokens / 1_000_000) * pricing["input"]
    cost += (completion_tokens / 1_000_000) * pricing["output"]

    return round(cost, 8)


def _append_csv_row(csv_path: str, row: dict, fieldnames: list[str]) -> None:
    """Agrega una fila a un CSV, creando el archivo (con header) si todavía no existe."""

    # crea la carpeta si no existe todavía
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    file_exists = os.path.isfile(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        if not file_exists:
            # BOM (Byte Order Mark): un puñado de bytes invisibles al
            # principio del archivo que le dicen a Excel "esto es UTF-8".
            # Sin esto, Excel en Windows suele adivinar mal el encoding y
            # muestra tildes/ñ rotas (mojibake), aunque el archivo esté
            # perfectamente bien escrito.
            f.write(chr(0xFEFF))
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# Columnas del CSV de métricas "de producción"

EXECUTION_FIELDNAMES = [
    "timestamp",
    "question",
    "model",
    "tokens_prompt",
    "tokens_completion",
    "total_tokens",
    "latency_ms",
    "estimated_cost_usd",
    "valid_json",
    "repaired",
]


def log_execution(csv_path: str, row: dict) -> None:
    """Agrega una fila de métricas de una ejecución real de run_query.py."""
    _append_csv_row(csv_path, row, EXECUTION_FIELDNAMES)


# Columnas del CSV del experimento de comparación de técnicas de prompt
COMPARISON_FIELDNAMES = [
    "timestamp",
    "variant",
    "question",
    "tokens_prompt",
    "tokens_completion",
    "total_tokens",
    "latency_ms",
    "estimated_cost_usd",
    "valid_json",
    "expected_action",
    "actions_returned",
    "correct",
]


def log_comparison_row(csv_path: str, row: dict) -> None:
    """Agrega una fila de resultados del experimento de comparación de
    técnicas de prompting."""
    _append_csv_row(csv_path, row, COMPARISON_FIELDNAMES)


def now_iso() -> str:
    """Timestamp actual en formato ISO 8601 (ej: 2026-09-13T14:03:42+00:00),
    en UTC para que sea consistente sin importar en qué huso horario
    corra el script.
    """
    return datetime.now(timezone.utc).isoformat()
