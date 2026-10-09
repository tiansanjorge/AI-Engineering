"""Tests del modulo de evaluacion y de la validez de los sets de prueba (sin API)."""

import pytest

from src.agents.orchestrator import OrchestratorResult
from src.agents.rag_agent import SourceRef
from src.evaluation import (
    BLIND_PATH,
    GOLDEN_PATH,
    HOLDOUT_PATH,
    INTENTS,
    aggregate,
    confusion_matrix,
    estimate_cost_usd,
    evaluate_case,
    load_golden,
    normalize,
    percentile,
)


def result(
    intent="hr", status="answered", answer="Son 21 días hábiles.", sections=("Sec A",)
):
    return OrchestratorResult(
        question="q",
        intent=intent,
        confidence=0.9,
        reason="r",
        status=status,
        answer=answer,
        sources=[
            SourceRef(chunk_id=f"c{i}", source="d.md", section=s)
            for i, s in enumerate(sections)
        ],
    )


def case(**kw):
    base = {
        "id": "X",
        "category": "tipica",
        "query": "q",
        "expected_intent": "hr",
        "expected_statuses": ["answered"],
    }
    return {**base, **kw}


@pytest.mark.parametrize("path", [GOLDEN_PATH, HOLDOUT_PATH, BLIND_PATH])
def test_test_sets_are_valid(path):
    cases = load_golden(path)
    assert len(cases) >= 10
    assert all(c["expected_statuses"] for c in cases)


def test_ids_are_unique_across_all_sets():
    ids = [
        c["id"] for p in (GOLDEN_PATH, HOLDOUT_PATH, BLIND_PATH) for c in load_golden(p)
    ]
    assert len(ids) == len(set(ids))


def test_dev_set_covers_all_intents_and_edge_categories():
    cases = load_golden(GOLDEN_PATH)
    assert {c["expected_intent"] for c in cases} == set(INTENTS)
    assert {"frontera", "ambigua", "fuera_de_alcance", "adversarial", "ruido"} <= {
        c["category"] for c in cases
    }
    assert len(cases) >= 30


def test_passing_case():
    ev = evaluate_case(
        case(expected_facts=["21"], expected_sections=["Sec A"]), result()
    )
    assert ev.passed and ev.routing_strict and ev.facts_ok and ev.sources_ok


def test_facts_are_compared_without_accents_or_case():
    assert normalize("Días HÁBILES") == "dias habiles"
    assert evaluate_case(
        case(expected_facts=["21 DIAS"]), result(answer="21 días")
    ).facts_ok


@pytest.mark.parametrize(
    ("kwargs", "res"),
    [
        ({"expected_facts": ["99"]}, result()),  # dato clave ausente
        ({"expected_sections": ["Otra"]}, result()),  # fuente esperada no citada
        ({"must_not_contain": ["21 días"]}, result()),  # frase prohibida presente
        ({}, result(intent="tech")),  # ruteo incorrecto
        ({}, result(status="abstained")),  # abstencion indebida
    ],
)
def test_failing_cases(kwargs, res):
    assert not evaluate_case(case(**kwargs), res).passed


def test_lenient_routing_accepts_alternative_intents_but_strict_does_not():
    ev = evaluate_case(
        case(acceptable_intents=["hr", "finance"]), result(intent="finance")
    )
    assert ev.routing_lenient and not ev.routing_strict and ev.passed


def test_false_answer_is_detected_when_should_not_answer():
    ev = evaluate_case(
        case(expected_intent="out_of_scope", expected_statuses=["out_of_scope"]),
        result(intent="hr"),
    )
    assert not ev.passed
    assert aggregate([ev])["false_answers"] == 1


def test_aggregate_counts_false_abstentions_and_builds_confusion_matrix():
    evals = [
        evaluate_case(case(id="1"), result()),
        evaluate_case(case(id="2"), result(status="abstained")),
        evaluate_case(case(id="3", expected_intent="tech"), result(intent="hr")),
    ]
    summary = aggregate(evals)
    assert summary["n"] == 3 and summary["false_abstentions"] == 1
    assert summary["pass_rate"] == pytest.approx(0.333, abs=1e-3)
    matrix = confusion_matrix(evals)
    assert matrix["hr"] == {"hr": 2} and matrix["tech"] == {"hr": 1}
    assert summary["per_class"]["hr"]["precision"] == pytest.approx(0.667, abs=1e-3)
    assert summary["per_class"]["tech"]["recall"] == 0.0


def test_percentile_and_cost():
    assert percentile([10, 20, 30, 40, 50], 50) == 30
    assert percentile([], 95) == 0.0
    assert estimate_cost_usd(1_000_000, 1_000_000) == pytest.approx(0.75)
