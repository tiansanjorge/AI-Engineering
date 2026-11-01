"""Metricas de evaluacion: que cuentan como acierto, falso positivo y estabilidad."""

import pytest

from src.evaluation import aggregate, evaluate, section_key
from src.models import ContractChangeOutput, ExtractedChange, ExtractionResult

EXPECTED = {
    "changes": [
        {"section": "Cláusula Tercera", "change_type": "modificacion"},
        {"section": "Cláusula Cuarta, inciso 4.3", "change_type": "eliminacion"},
    ],
    "key_facts_in_summary": ["Chile", "4.3"],
}
RESUMEN = "Se suma Chile al alcance territorial y se elimina el inciso 4.3 de las restricciones."


def _detail(*changes, summary=RESUMEN):
    items = [
        ExtractedChange(
            section=s, change_type=t, topic="Tema", description="descripcion"
        )
        for s, t in changes
    ]
    return ExtractionResult(changes=items, summary_of_the_change=summary)


def _eval(detail):
    return evaluate(EXPECTED, detail.to_output(), detail)


@pytest.mark.parametrize(
    "a,b",
    [
        ("Cláusula Cuarta, inciso 4.3", "inciso 4.3 de la CLÁUSULA CUARTA"),
        ("Cláusula Séptima", "CLAUSULA SEPTIMA"),
    ],
)
def test_section_key_ignora_redaccion_acentos_y_orden(a, b):
    assert section_key(a) == section_key(b)


def test_corrida_perfecta():
    row = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"),
            ("Cláusula Cuarta, inciso 4.3", "eliminacion"),
        )
    )
    assert row["perfect"] and row["type_correct"] == 2 and row["false_positives"] == []


def test_seccion_omitida_baja_la_cobertura():
    row = _eval(_detail(("Cláusula Tercera", "modificacion")))
    assert row["sections_found"] == 1 and not row["perfect"]


def test_tipo_de_cambio_equivocado():
    row = _eval(
        _detail(
            ("Cláusula Tercera", "adicion"),
            ("Cláusula Cuarta, inciso 4.3", "eliminacion"),
        )
    )
    assert row["type_correct"] == 1 and not row["perfect"]


def test_reportar_un_inciso_que_no_cambio_es_falso_positivo():
    # Defecto que tenia la primera version: 4.1 comparte ordinal con 4.3 y pasaba inadvertido.
    row = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"),
            ("Cláusula Cuarta, inciso 4.3", "eliminacion"),
            ("Cláusula Cuarta, inciso 4.1", "modificacion"),
        )
    )
    assert row["false_positives"] == ["cuarta 4.1"] and not row["perfect"]


def test_clausula_cuarta_a_secas_cubre_al_inciso():
    row = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"), ("Cláusula Cuarta", "eliminacion")
        )
    )
    assert row["sections_found"] == 2 and row["false_positives"] == []


def test_deteccion_de_la_advertencia_y_hechos_clave():
    row = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"),
            summary=RESUMEN + " Advertencia: fecha inconsistente.",
        )
    )
    assert row["has_warning"] and row["facts_found"] == 2


def test_sin_detalle_no_se_miden_tipos():
    out = ContractChangeOutput(
        sections_changed=["Cláusula Tercera"],
        topics_touched=["T"],
        summary_of_the_change=RESUMEN,
    )
    row = evaluate(EXPECTED, out)
    assert row["type_correct"] is None


def test_aggregate_estabilidad_y_promedios():
    ok = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"),
            ("Cláusula Cuarta, inciso 4.3", "eliminacion"),
        )
    )
    bad = _eval(_detail(("Cláusula Tercera", "modificacion")))
    agg = aggregate([ok, ok, bad])
    assert agg["runs"] == 3 and agg["perfect_runs"] == 2
    assert agg["recall"] == pytest.approx(5 / 6)
    assert agg["stable"] is False
    assert aggregate([ok, ok])["stable"] is True


def test_muletilla_sobre_alertas_se_detecta_y_quita_la_perfeccion():
    row = _eval(
        _detail(
            ("Cláusula Tercera", "modificacion"),
            ("Cláusula Cuarta, inciso 4.3", "eliminacion"),
            summary=RESUMEN + " No se reportan alertas en el mapa contextual.",
        )
    )
    assert row["has_filler"] and not row["perfect"]


def test_una_advertencia_real_no_es_muletilla():
    summary = RESUMEN + " Advertencia: alerta de fechas."
    row = _eval(_detail(("Cláusula Tercera", "modificacion"), summary=summary))
    assert row["has_warning"] and not row["has_filler"]
