"""Consistencia de los contratos de prueba: cada par tiene sus imagenes y un ground truth valido."""

import json

import pytest

from src import config

CASES = sorted(p for p in config.TEST_CONTRACTS_DIR.iterdir() if p.is_dir())
CHANGE_TYPES = {"modificacion", "eliminacion", "adicion"}


def test_hay_al_menos_dos_pares():
    # Requisito de la consigna: minimo 2 pares (4 imagenes).
    assert len(CASES) >= 2


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.name)
def test_par_completo_y_ground_truth_valido(case):
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    for key in ("original", "amendment"):
        assert (case / expected["images"][key]).is_file()
        assert expected["documents"][key].strip()
    assert expected["changes"], "un par sin cambios no sirve como caso de prueba"
    assert {c["change_type"] for c in expected["changes"]} <= CHANGE_TYPES
    # Una clausula no puede ser a la vez cambiada y "sin cambios".
    changed = {c["section"] for c in expected["changes"]}
    assert not changed & set(expected["unchanged_sections"])
