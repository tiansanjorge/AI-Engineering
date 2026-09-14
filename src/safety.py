"""Defensa en capas contra entradas adversariales (bonus de seguridad).

Por qué "en capas" y no una sola barrera: una única línea de defensa es
fácil de esquivar con una variación mínima del ataque. Acá hay dos
chequeos independientes, en dos momentos distintos:

1. detect_adversarial_input — se corre ANTES de llamar al modelo. Si la
   pregunta del usuario intenta manipular el comportamiento del asistente
   (pedirle que ignore sus instrucciones, revele el prompt de sistema,
   etc.), ni siquiera se gasta una llamada a la API: se corta ahí.

2. detect_unsafe_output — se corre DESPUÉS de tener la respuesta del
   modelo. Es la red de seguridad para el caso en que el ataque no haya
   usado ninguna de las frases conocidas de la capa 1, pero el modelo
   terminó igual filtrando parte de sus instrucciones internas en la
   respuesta.

Ninguna de las dos capas llama a la API — son funciones puras, testeables
sin gastar nada ni depender de que OpenAI esté disponible.
"""

import re

# Frases típicas de "prompt injection": intentos de que el usuario, desde
# la pregunta, se comporte como si tuviera la misma autoridad que el
# prompt de sistema. La lista no pretende ser exhaustiva (nunca lo es,
# ver la limitación documentada en el README) — cubre los patrones más
# comunes en español e inglés.
ADVERSARIAL_PATTERNS = [
    r"ignora?\s+(todas?\s+)?(tus\s+)?(las\s+)?instruccion",
    r"olvida?\s+(todas?\s+)?(tus\s+)?(las\s+)?(reglas|instruccion)",
    r"revela?\s+.*(prompt|instruccion)",
    r"mu[eé]stra\s+.*(prompt\s+del\s+sistema|system\s+prompt)",
    r"modo\s+desarrollador",
    r"developer\s+mode",
    r"jailbreak",
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions)",
    r"act(u|ú)a\s+como\s+si\s+no\s+tuvieras\s+reglas",
    r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?ai\s+without",
]

# Cantidad mínima de palabras consecutivas del prompt de sistema que,
# si aparecen calcadas en la respuesta, se consideran una fuga (no un
# número mágico: lo suficientemente largo para que no sea casualidad que
# dos textos compartan esa secuencia exacta de palabras).
MIN_LEAK_WORDS = 8


def detect_adversarial_input(question: str) -> list[str]:
    """Capa 1: revisa la pregunta ANTES de llamar al modelo.

    Devuelve una lista de motivos de rechazo (vacía si no se detectó
    nada sospechoso) — mismo patrón que validate_response en schema.py.
    """
    reasons = []
    lowered = question.lower()
    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, lowered):
            reasons.append(f"la pregunta contiene un patrón de prompt injection ('{pattern}')")
    return reasons


def detect_unsafe_output(answer: str, system_prompt: str) -> list[str]:
    """Capa 2: revisa la respuesta final DESPUÉS de llamar al modelo.

    Dos chequeos independientes:
    - ¿La respuesta repite alguno de los mismos patrones de ataque? (el
      modelo podría estar "obedeciendo" y confirmando el intento).
    - ¿La respuesta contiene un fragmento largo y literal del prompt de
      sistema? (indicio de que el modelo filtró sus instrucciones).
    """
    reasons = []
    lowered_answer = answer.lower()

    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, lowered_answer):
            reasons.append(f"la respuesta repite un patrón sospechoso ('{pattern}')")

    prompt_words = system_prompt.split()
    for i in range(len(prompt_words) - MIN_LEAK_WORDS + 1):
        window = " ".join(prompt_words[i : i + MIN_LEAK_WORDS]).lower()
        if window and window in lowered_answer:
            reasons.append("la respuesta contiene un fragmento literal del prompt de sistema (posible fuga)")
            break

    return reasons
