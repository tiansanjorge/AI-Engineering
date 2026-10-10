"""Evaluacion del sistema contra el golden set (`test_queries.json`).

Todo es deterministico y no usa un LLM como juez (el juez es el bonus de la Fase 7):

- **Ruteo**: `routing_strict` (intencion == esperada) y `routing_lenient` (intencion dentro de las
  aceptables: hay consultas genuinamente ambiguas con mas de una area valida).
- **Estado**: el resultado final (`answered`, `abstained`, `out_of_scope`, `error`) esta entre los
  esperados. Detecta tanto abstenciones indebidas como respuestas a lo que no se debia responder.
- **Contenido**: `facts_ok` (los datos clave esperados aparecen en la respuesta), `sources_ok`
  (una de las secciones esperadas fue citada) y `forbidden_ok` (la respuesta no contiene frases
  prohibidas, p. ej. filtrar el prompt o "aprobar" algo que un asistente no puede aprobar).
"""

import json
import unicodedata
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from src.agents.orchestrator import OrchestratorResult
from src.config import MODULE_ROOT

GOLDEN_PATH = MODULE_ROOT / "test_queries.json"
HOLDOUT_PATH = MODULE_ROOT / "test_queries_holdout.json"
BLIND_PATH = MODULE_ROOT / "test_queries_blind.json"
INTENTS = ["hr", "tech", "finance", "out_of_scope"]
# Precio de gpt-4o-mini en USD por millon de tokens (mismo que modulo-1/config/pricing.json).
CHAT_PRICE_PER_M_TOKENS = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00)}


class CaseEval(BaseModel):
    id: str
    category: str
    query: str
    expected_intent: str
    expected_statuses: list[str]
    routed_intent: str | None
    status: str
    answer: str
    cited_sections: list[str]
    routing_strict: bool
    routing_lenient: bool
    status_ok: bool
    facts_ok: bool | None
    sources_ok: bool | None
    forbidden_ok: bool
    passed: bool
    low_confidence: bool
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    trace_id: str | None = None
    quality_score: int | None = None
    quality_reason: str | None = None
    judge_input_tokens: int = 0
    judge_output_tokens: int = 0


def load_golden(path: Path = GOLDEN_PATH) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Hay ids duplicados en el golden set")
    for case in cases:
        if case["expected_intent"] not in INTENTS:
            raise ValueError(f"{case['id']}: expected_intent invalido")
        if not set(case.get("acceptable_intents", [])) <= set(INTENTS):
            raise ValueError(f"{case['id']}: acceptable_intents invalido")
    return cases


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def evaluate_case(case: dict, result: OrchestratorResult) -> CaseEval:
    acceptable = set(case.get("acceptable_intents") or [case["expected_intent"]])
    acceptable.add(case["expected_intent"])
    answer = normalize(result.answer)
    cited = [s.section for s in result.sources]

    facts = case.get("expected_facts")
    facts_ok = None if not facts else all(normalize(f) in answer for f in facts)
    sections = case.get("expected_sections")
    sources_ok = None if not sections else any(s in sections for s in cited)
    forbidden_ok = not any(
        normalize(p) in answer for p in case.get("must_not_contain", [])
    )

    routing_strict = result.intent == case["expected_intent"]
    routing_lenient = result.intent in acceptable
    status_ok = result.status in case["expected_statuses"]
    passed = (
        routing_lenient
        and status_ok
        and facts_ok is not False
        and sources_ok is not False
        and forbidden_ok
    )
    return CaseEval(
        id=case["id"],
        category=case["category"],
        query=case["query"],
        expected_intent=case["expected_intent"],
        expected_statuses=case["expected_statuses"],
        routed_intent=result.intent,
        status=result.status,
        answer=result.answer,
        cited_sections=cited,
        routing_strict=routing_strict,
        routing_lenient=routing_lenient,
        status_ok=status_ok,
        facts_ok=facts_ok,
        sources_ok=sources_ok,
        forbidden_ok=forbidden_ok,
        passed=passed,
        low_confidence=result.low_confidence,
    )


def confusion_matrix(evals: list[CaseEval]) -> dict[str, dict[str, int]]:
    """Filas = intencion esperada, columnas = intencion ruteada (`error` si el router fallo)."""
    matrix = {e: Counter() for e in INTENTS}
    for ev in evals:
        matrix[ev.expected_intent][ev.routed_intent or "error"] += 1
    return {row: dict(cols) for row, cols in matrix.items()}


def _rate(values: list[bool]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
    return round(ordered[index], 1)


def estimate_cost_usd(
    input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini"
) -> float:
    price_in, price_out = CHAT_PRICE_PER_M_TOKENS[model]
    return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)


def aggregate(evals: list[CaseEval]) -> dict:
    """Metricas agregadas de una corrida."""
    n = len(evals)
    expected_to_answer = [e for e in evals if set(e.expected_statuses) == {"answered"}]
    should_not_answer = [e for e in evals if "answered" not in e.expected_statuses]
    per_class = {}
    for intent in INTENTS:
        tp = sum(
            1
            for e in evals
            if e.routed_intent == intent and e.expected_intent == intent
        )
        routed = sum(1 for e in evals if e.routed_intent == intent)
        expected = sum(1 for e in evals if e.expected_intent == intent)
        per_class[intent] = {
            "precision": round(tp / routed, 3) if routed else None,
            "recall": round(tp / expected, 3) if expected else None,
            "support": expected,
        }
    by_category = {}
    for category in sorted({e.category for e in evals}):
        subset = [e for e in evals if e.category == category]
        by_category[category] = {
            "n": len(subset),
            "pass_rate": _rate([e.passed for e in subset]),
        }
    latencies = [e.latency_ms for e in evals]
    in_tokens, out_tokens = (
        sum(e.input_tokens for e in evals),
        sum(e.output_tokens for e in evals),
    )
    return {
        "n": n,
        "pass_rate": _rate([e.passed for e in evals]),
        "routing_strict": _rate([e.routing_strict for e in evals]),
        "routing_lenient": _rate([e.routing_lenient for e in evals]),
        "status_ok": _rate([e.status_ok for e in evals]),
        "facts_ok": _rate([e.facts_ok for e in evals if e.facts_ok is not None]),
        "sources_ok": _rate([e.sources_ok for e in evals if e.sources_ok is not None]),
        "forbidden_ok": _rate([e.forbidden_ok for e in evals]),
        "false_abstentions": sum(
            1 for e in expected_to_answer if e.status != "answered"
        ),
        "false_answers": sum(1 for e in should_not_answer if e.status == "answered"),
        "low_confidence_rate": _rate([e.low_confidence for e in evals]),
        "per_class": per_class,
        "by_category": by_category,
        "confusion_matrix": confusion_matrix(evals),
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "estimated_cost_usd": estimate_cost_usd(in_tokens, out_tokens),
        **quality_summary(evals),
    }


def _ranks(values: list[float]) -> list[float]:
    """Rangos (empezando en 1) con promedio en los empates."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    """Correlacion de Spearman (Pearson sobre rangos); None si una serie es constante."""
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("Se necesitan dos series de la misma longitud (>= 2)")
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    var_x = sum((a - mx) ** 2 for a in rx)
    var_y = sum((b - my) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return None
    return round(cov / (var_x * var_y) ** 0.5, 3)


def judge_agreement(
    human: list[int], judge: list[int], good_threshold: int = 7
) -> dict:
    """Acuerdo entre el juez y las etiquetas humanas.

    `bias` > 0 significa que el juez es mas generoso que la persona. `false_good` son respuestas
    que la persona considera malas (< umbral) y el juez buenas: el error mas peligroso de un juez.
    """
    n = len(human)
    diffs = [j - h for h, j in zip(human, judge, strict=True)]
    return {
        "n": n,
        "spearman": spearman(human, judge),
        "mae": round(sum(abs(d) for d in diffs) / n, 2),
        "bias": round(sum(diffs) / n, 2),
        "within_1": round(sum(abs(d) <= 1 for d in diffs) / n, 3),
        "within_2": round(sum(abs(d) <= 2 for d in diffs) / n, 3),
        "binary_agreement": round(
            sum(
                (h >= good_threshold) == (j >= good_threshold)
                for h, j in zip(human, judge, strict=True)
            )
            / n,
            3,
        ),
        "false_good": sum(
            h < good_threshold <= j for h, j in zip(human, judge, strict=True)
        ),
        "false_bad": sum(
            j < good_threshold <= h for h, j in zip(human, judge, strict=True)
        ),
    }


def quality_summary(evals: list[CaseEval], judge_model: str = "gpt-4o") -> dict:
    """Resumen de los puntajes del evaluador (vacio si no se uso el juez en la corrida)."""
    scored = [e for e in evals if e.quality_score is not None]
    if not scored:
        return {
            "scored": 0,
            "mean_quality": None,
            "low_quality_count": None,
            "judge_cost_usd": None,
        }
    judge_in = sum(e.judge_input_tokens for e in evals)
    judge_out = sum(e.judge_output_tokens for e in evals)
    return {
        "scored": len(scored),
        "mean_quality": round(sum(e.quality_score for e in scored) / len(scored), 2),
        "low_quality_count": sum(e.quality_score < 7 for e in scored),
        "judge_cost_usd": estimate_cost_usd(judge_in, judge_out, judge_model),
    }
