"""Contrato Pydantic: que acepta, que rechaza y como se deriva la salida publica."""

import pytest
from pydantic import ValidationError

from src.models import (
    ChangeType,
    ContractChangeOutput,
    ExtractedChange,
    ExtractionResult,
)

RESUMEN = (
    "Se modifica el monto mensual de USD 2.500 a USD 2.800 y se extiende la vigencia."
)


def _change(**over):
    base = {
        "section": "Cláusula Tercera",
        "change_type": "modificacion",
        "topic": "Precio",
        "description": "El monto mensual pasa de USD 2.500 a USD 2.800.",
    }
    return ExtractedChange(**{**base, **over})


def _output(**over):
    base = {
        "sections_changed": ["C2"],
        "topics_touched": ["Precio"],
        "summary_of_the_change": RESUMEN,
    }
    return ContractChangeOutput(**{**base, **over})


def test_output_valido_y_normaliza():
    out = _output(
        sections_changed=[
            "  Cláusula   Segunda ",
            "cláusula segunda",
            "Cláusula Tercera",
        ]
    )
    # Espacios colapsados y duplicados (sin distinguir mayusculas) eliminados, orden conservado.
    assert out.sections_changed == ["Cláusula Segunda", "Cláusula Tercera"]


@pytest.mark.parametrize("campo", ["sections_changed", "topics_touched"])
def test_listas_vacias_se_rechazan(campo):
    with pytest.raises(ValidationError, match="no puede estar vacia"):
        _output(**{campo: []})


def test_item_vacio_en_lista_se_rechaza():
    with pytest.raises(ValidationError, match="elementos vacios"):
        _output(sections_changed=["C2", "  "])


def test_resumen_corto_se_rechaza():
    with pytest.raises(ValidationError, match="demasiado corto"):
        _output(summary_of_the_change="ok")


def test_campos_extra_se_rechazan():
    with pytest.raises(ValidationError):
        _output(extra="x")


def test_tipo_de_cambio_invalido():
    with pytest.raises(ValidationError):
        _change(change_type="actualizacion")


def test_extraction_result_exige_al_menos_un_cambio():
    with pytest.raises(ValidationError, match="al menos un cambio"):
        ExtractionResult(changes=[], summary_of_the_change=RESUMEN)


def test_to_output_deriva_secciones_y_temas_del_detalle():
    result = ExtractionResult(
        changes=[
            _change(),
            _change(
                section="Cláusula Octava",
                change_type="adicion",
                topic="Datos personales",
            ),
        ],
        summary_of_the_change=RESUMEN,
    )
    out = result.to_output()
    assert out.sections_changed == ["Cláusula Tercera", "Cláusula Octava"]
    assert out.topics_touched == ["Precio", "Datos personales"]
    assert result.changes[1].change_type is ChangeType.ADDITION


def test_el_json_de_salida_tiene_exactamente_los_tres_campos():
    assert set(_output().model_dump()) == {
        "sections_changed",
        "topics_touched",
        "summary_of_the_change",
    }
