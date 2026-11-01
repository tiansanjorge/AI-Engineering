"""Pipeline completo y CLI con modelos simulados: orden, handoff, fallo rapido y errores claros."""

import json

import pytest
from PIL import Image

from src import config, main
from src.errors import ConfigError, InvalidImageError, OutputValidationError
from src.models import ContractChangeOutput

SALIDA = ContractChangeOutput(
    sections_changed=["Cláusula Tercera"],
    topics_touched=["Precio"],
    summary_of_the_change="El monto mensual pasa de USD 2.500 a USD 2.800 por acuerdo de partes.",
)


class FakeContextualizer:
    def __init__(self, log):
        self.log = log

    def run(self, original, amendment, run_config=None):
        self.log.append(("contextualizer", original, amendment))
        return "MAPA"


class FakeExtractor:
    last_attempts = 1

    def __init__(self, log, error=None):
        self.log, self.error = log, error

    def run(self, context_map, original, amendment, run_config=None):
        self.log.append(("extractor", context_map, original, amendment))
        if self.error:
            raise self.error
        return SALIDA


@pytest.fixture
def images(tmp_path):
    paths = []
    for name in ("original.png", "adenda.png"):
        path = tmp_path / name
        Image.new("RGB", (30, 30), "white").save(path)
        paths.append(path)
    return paths


def _fake_parse(log):
    def parse(path, run_config=None):
        log.append(("parse", path.name))
        return f"TEXTO[{path.name}]"

    return parse


def test_pipeline_orden_y_handoff(images):
    log = []
    result = main.analyze_contracts(
        *images,
        parse_fn=_fake_parse(log),
        contextualizer=FakeContextualizer(log),
        extractor=FakeExtractor(log),
    )
    assert [e[0] for e in log] == ["parse", "parse", "contextualizer", "extractor"]
    # El agente 1 recibe los dos textos parseados; el agente 2 recibe SU mapa y los dos textos.
    assert log[2] == ("contextualizer", "TEXTO[original.png]", "TEXTO[adenda.png]")
    assert log[3] == ("extractor", "MAPA", "TEXTO[original.png]", "TEXTO[adenda.png]")
    assert result.output == SALIDA
    assert [s.name for s in result.stages] == [
        "parse_original_contract",
        "parse_amendment_contract",
        "contextualization_agent",
        "extraction_agent",
    ]


def test_falla_rapido_si_la_segunda_imagen_es_invalida(images, tmp_path):
    log = []
    with pytest.raises(InvalidImageError):
        main.analyze_contracts(
            images[0],
            tmp_path / "no_existe.png",
            parse_fn=_fake_parse(log),
            contextualizer=FakeContextualizer(log),
            extractor=FakeExtractor(log),
        )
    assert log == []  # no se gasto ni una llamada al modelo


def test_error_del_agente_se_propaga(images):
    log = []
    with pytest.raises(OutputValidationError):
        main.analyze_contracts(
            *images,
            parse_fn=_fake_parse(log),
            contextualizer=FakeContextualizer(log),
            extractor=FakeExtractor(
                log, error=OutputValidationError("salida invalida")
            ),
        )


def test_cli_sin_api_key_da_mensaje_claro(images, monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main.main([str(images[0]), str(images[1])]) == 1
    assert "ConfigError" in capsys.readouterr().err


def test_cli_imagen_inexistente_no_muestra_traceback(images, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert main.main([str(images[0]), "no_existe.png"]) == 1
    err = capsys.readouterr().err
    assert "InvalidImageError" in err and "Traceback" not in err


def test_cli_exito_imprime_json_y_lo_guarda(images, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake = main.AnalysisResult(output=SALIDA, stages=[], trace_id=None, trace_url=None)
    monkeypatch.setattr(main, "analyze_contracts", lambda *a, **k: fake)
    out = tmp_path / "resultado.json"
    assert main.main([str(images[0]), str(images[1]), "--output", str(out)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert set(printed) == {
        "sections_changed",
        "topics_touched",
        "summary_of_the_change",
    }
    assert json.loads(out.read_text(encoding="utf-8")) == printed


def test_require_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        config.require_openai_key()
