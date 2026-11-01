"""Metricas para medir la fidelidad del parsing contra el texto correcto (ground truth).

Se usa Word Error Rate (WER), la misma metrica de la Lecture 2: minimo de sustituciones,
inserciones y borrados de palabras para convertir la hipotesis en la referencia, dividido por la
cantidad de palabras de la referencia. 0.0 = transcripcion perfecta.
"""

from difflib import SequenceMatcher


def _words(text: str) -> list[str]:
    # Solo se normaliza el espacio en blanco: mayusculas, tildes y puntuacion CUENTAN, porque en
    # un contrato "2.800" vs "2,800" es un error real.
    return text.split()


def word_error_rate(reference: str, hypothesis: str) -> float:
    """WER por distancia de edicion (Levenshtein) sobre palabras."""
    ref, hyp = _words(reference), _words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            cost = 0 if r == h else 1
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1] / len(ref)


def char_similarity(reference: str, hypothesis: str) -> float:
    """Similitud de caracteres entre 0 y 1 (1.0 = identico), ignorando espacios repetidos."""
    ref, hyp = " ".join(reference.split()), " ".join(hypothesis.split())
    return SequenceMatcher(None, ref, hyp, autojunk=False).ratio()
