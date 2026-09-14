"""Contrato de salida del asistente y su validación."""

REQUIRED_FIELDS = ("answer", "confidence", "actions")

VALID_ACTIONS = {
    "responder_directamente",
    "escalar_a_humano",
    "pedir_mas_informacion",
    "crear_ticket_bug",
    "cerrar_ticket_duplicado",
}


def validate_response(data: dict) -> list[str]:
    """Valida el JSON devuelto por el modelo contra el contrato esperado."""

    errors = []

    if not isinstance(data, dict):
        return ["la respuesta no es un objeto JSON"]

    # Recorremos cada campo obligatorio y nos fijamos si está presente en el diccionario.
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"falta el campo requerido '{field}'")

    if "reasoning" in data:
        reasoning = data["reasoning"]

        if not isinstance(reasoning, list) or len(reasoning) == 0:
            errors.append("'reasoning' debe ser una lista no vacía de strings")

    if "answer" in data:

        if not isinstance(data["answer"], str) or not data["answer"].strip():
            errors.append("'answer' debe ser un string no vacío")

    if "confidence" in data:
        confidence = data["confidence"]

        is_number = isinstance(confidence, (int, float)) and not isinstance(
            confidence, bool
        )
        if not is_number or not (0.0 <= float(confidence) <= 1.0):
            errors.append("'confidence' debe ser un número entre 0.0 y 1.0")

    if "actions" in data:
        actions = data["actions"]
        if not isinstance(actions, list) or len(actions) == 0:
            errors.append("'actions' debe ser una lista no vacía")

        elif not all(a in VALID_ACTIONS for a in actions):
            errors.append(f"'actions' solo admite valores de {sorted(VALID_ACTIONS)}")

    return errors


def fallback_response(reason: str) -> dict:
    """JSON de emergencia cuando el modelo rompe el contrato."""

    return {
        "reasoning": [f"El modelo no devolvió un JSON válido: {reason}"],
        "answer": "No se pudo generar una respuesta confiable de forma automática. Se escala a un agente humano.",
        "confidence": 0.0,
        "actions": ["escalar_a_humano"],
    }
