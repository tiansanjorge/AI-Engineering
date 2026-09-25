"""Agente evaluador (bonus): puntua la calidad de una respuesta del RAG.

Recibe la salida ya generada por query.py (user_question, system_answer,
chunks_related) y le pide a un LLM que la juzgue en 3 dimensiones:
relevancia de los chunks, fidelidad al contexto, y completitud.
"""

import json
import os

from openai import OpenAI

DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """Sos un evaluador de calidad para un sistema de RAG de FAQs. Te paso la pregunta de un usuario, la respuesta que dio el sistema, y los fragmentos de documentacion que uso para responder.

Evalua 3 dimensiones:
1. Relevancia de los chunks: ¿los fragmentos recuperados se relacionan con la pregunta?
2. Fidelidad: ¿la respuesta usa solo informacion presente en los fragmentos, sin inventar nada?
3. Completitud: ¿la respuesta cubre la pregunta por completo, o falta algo que los fragmentos si tenian?

Antes de escribir cada observacion, releé con cuidado el texto completo de
la respuesta palabra por palabra. Si vas a decir que algo "falta" en la
respuesta, primero confirmá que ese dato no aparece en ningun lado del
texto de la respuesta — si aparece, no lo cuentes como faltante.

Devolve SOLO un JSON con dos claves:
- "score": entero de 0 a 10
- "reason": string de al menos 50 caracteres que justifique el puntaje. Cada observacion sobre algo que la respuesta dice o no dice debe ir acompañada de una cita textual entre comillas (de la respuesta o de un fragmento) que la respalde."""


def build_evaluation_prompt(
    user_question: str, system_answer: str, chunks_related: list[str]
) -> str:
    """Arma el mensaje de usuario para el evaluador."""
    chunks_text = "\n\n".join(
        f"[Fragmento {i + 1}] {c}" for i, c in enumerate(chunks_related)
    )
    return (
        f"Pregunta: {user_question}\n\n"
        f"Respuesta del sistema: {system_answer}\n\n"
        f"Fragmentos usados:\n{chunks_text}"
    )


def evaluate_response(
    user_question: str,
    system_answer: str,
    chunks_related: list[str],
    model: str = DEFAULT_CHAT_MODEL,
) -> dict:
    """Le pide al LLM que puntue la respuesta y devuelve {"score", "reason"}."""
    client = OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_evaluation_prompt(
                    user_question, system_answer, chunks_related
                ),
            },
        ],
        temperature=0,
        max_completion_tokens=300,
        response_format={"type": "json_object"},
    )
    result = json.loads(completion.choices[0].message.content)
    return {"score": int(result["score"]), "reason": str(result["reason"])}
