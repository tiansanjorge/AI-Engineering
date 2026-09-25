"""Generacion de la respuesta final con el LLM, usando el contexto recuperado."""

import os

from openai import OpenAI

DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

# Las reglas que hacen que esto sea RAG y no "un modelo con texto pegado
# adelante": responder solo con el contexto, extraer lo relevante aunque
# no calce exacto con la pregunta, admitir cuando de verdad no esta, y
# ser conciso.
#
# La regla 2 se agrego despues de un hallazgo real: con solo "si no esta,
# decilo", el modelo rechazaba preguntas donde el fragmento SI tenia la
# respuesta pero no en las mismas palabras que la pregunta (ver Fase 3 /
# README). "Rechazo solo si ningun fragmento se relaciona" corrige eso
# sin volver a permitir que invente.
SYSTEM_PROMPT = """Sos el asistente de soporte de NimbusHR (RRHH). Respondes preguntas de empleados usando EXCLUSIVAMENTE los fragmentos de documentacion que te paso a continuacion.

Reglas:
1. Responde solo con informacion presente en los fragmentos. No completes con conocimiento externo.
2. Si algun fragmento tiene informacion relacionada con la pregunta, aunque no la responda con las mismas palabras, extraela y usala para responder. Rechaza responder ("No encuentro esa informacion en la documentacion disponible") solo cuando NINGUN fragmento se relacione con la pregunta.
3. Se conciso: 2 a 4 oraciones."""


def build_prompt(question: str, chunks: list[str]) -> str:
    """Arma el mensaje de usuario: el contexto recuperado + la pregunta."""
    context = "\n\n".join(f"[Fragmento {i + 1}] {c}" for i, c in enumerate(chunks))
    return f"Contexto:\n{context}\n\nPregunta: {question}"


def generate_answer(
    question: str, chunks: list[str], model: str = DEFAULT_CHAT_MODEL
) -> str:
    """Etapa 4 del pipeline de consulta: le pide al LLM que responda
    usando unicamente los chunks recuperados."""
    client = OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, chunks)},
        ],
        temperature=0.2,
        max_completion_tokens=300,
    )
    return completion.choices[0].message.content.strip()
