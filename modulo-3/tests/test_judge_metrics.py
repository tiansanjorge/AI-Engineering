"""Tests de las metricas de acuerdo juez-humano y del resumen de calidad (sin red)."""

import pytest

from src.agents.orchestrator import OrchestratorResult
from src.evaluation import evaluate_case, judge_agreement, quality_summary, spearman


def test_spearman_perfect_inverse_and_constant_series():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert spearman([1, 1, 1], [1, 2, 3]) is None  # serie constante: indefinida
    assert spearman([1, 2, 2, 3], [1, 2, 2, 3]) == 1.0  # empates con rango promedio


def test_spearman_rejects_mismatched_or_tiny_series():
    with pytest.raises(ValueError):
        spearman([1, 2], [1])
    with pytest.raises(ValueError):
        spearman([1], [1])


def test_judge_agreement_metrics():
    human = [10, 9, 2, 3, 1]
    judge = [10, 10, 8, 3, 1]  # una respuesta mala (2) que el juez da por buena (8)
    m = judge_agreement(human, judge)
    assert m["n"] == 5 and m["false_good"] == 1 and m["false_bad"] == 0
    assert m["mae"] == pytest.approx(1.4) and m["bias"] == pytest.approx(1.4)
    assert m["within_1"] == pytest.approx(0.8)
    assert m["binary_agreement"] == pytest.approx(0.8)


def test_quality_summary_only_when_judge_was_used():
    case = {
        "id": "a",
        "category": "tipica",
        "query": "q",
        "expected_intent": "hr",
        "expected_statuses": ["answered"],
    }
    result = OrchestratorResult(
        question="q",
        intent="hr",
        status="answered",
        answer="x",
        confidence=0.9,
        reason="r",
    )
    plain = evaluate_case(case, result)
    assert quality_summary([plain])["mean_quality"] is None
    scored = plain.model_copy(
        update={
            "quality_score": 6,
            "judge_input_tokens": 1000,
            "judge_output_tokens": 100,
        }
    )
    summary = quality_summary([scored], judge_model="gpt-4o")
    assert summary["scored"] == 1 and summary["mean_quality"] == 6
    assert summary["low_quality_count"] == 1
    assert summary["judge_cost_usd"] == pytest.approx(0.0035)
