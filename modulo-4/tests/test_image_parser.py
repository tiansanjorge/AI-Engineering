"""Parser de imagenes: validacion de entrada, codificacion y manejo de errores. Sin API real."""

import httpx
import openai
import pytest
from PIL import Image

from src import config
from src.errors import EmptyParseError, InvalidImageError, VisionAPIError
from src.image_parser import encode_image, parse_contract_image, validate_image
from src.text_metrics import char_similarity, word_error_rate


class FakeLLM:
    """Modelo falso: guarda los mensajes recibidos y devuelve una respuesta fija."""

    def __init__(self, content="TEXTO TRANSCRIPTO", error=None):
        self.content, self.error, self.messages = content, error, None

    def invoke(self, messages, config=None):
        self.messages = messages
        if self.error:
            raise self.error
        return type("Resp", (), {"content": self.content})()


@pytest.fixture
def png(tmp_path):
    path = tmp_path / "doc.png"
    Image.new("RGB", (40, 40), "white").save(path)
    return path


def test_validate_imagen_inexistente(tmp_path):
    with pytest.raises(InvalidImageError, match="No existe"):
        validate_image(tmp_path / "nada.png")


def test_validate_formato_no_soportado(tmp_path):
    bad = tmp_path / "doc.pdf"
    bad.write_bytes(b"x")
    with pytest.raises(InvalidImageError, match="Formato no soportado"):
        validate_image(bad)


def test_validate_archivo_vacio(tmp_path):
    empty = tmp_path / "doc.png"
    empty.write_bytes(b"")
    with pytest.raises(InvalidImageError, match="vacio"):
        validate_image(empty)


def test_validate_imagen_muy_pesada(png, monkeypatch):
    monkeypatch.setattr(config, "MAX_IMAGE_MB", 0.00001)
    with pytest.raises(InvalidImageError, match="maximo"):
        validate_image(png)


def test_encode_rechaza_archivo_corrupto_con_extension_falsa(tmp_path):
    fake = tmp_path / "doc.png"
    fake.write_text("esto no es una imagen")
    with pytest.raises(InvalidImageError, match="no es una imagen valida"):
        encode_image(validate_image(fake))


def test_encode_usa_el_formato_real_no_la_extension(tmp_path):
    # Un JPEG guardado con extension .png debe declararse como image/jpeg.
    path = tmp_path / "doc.png"
    Image.new("RGB", (20, 20), "white").save(path, format="JPEG")
    assert encode_image(path).startswith("data:image/jpeg;base64,")


def test_parse_arma_el_mensaje_multimodal_y_devuelve_texto(png):
    llm = FakeLLM("  CLAUSULA PRIMERA  ")
    assert parse_contract_image(png, llm=llm) == "CLAUSULA PRIMERA"
    system, human = llm.messages
    assert "fiel" in system.content
    image_part = human.content[1]
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    assert image_part["image_url"]["detail"] == "high"


def test_parse_respuesta_vacia(png):
    with pytest.raises(EmptyParseError):
        parse_contract_image(png, llm=FakeLLM("   "))


def test_parse_traduce_error_de_api(png):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = openai.APIConnectionError(request=request)
    with pytest.raises(VisionAPIError, match="APIConnectionError"):
        parse_contract_image(png, llm=FakeLLM(error=error))


def test_parse_no_llama_a_la_api_si_la_imagen_es_invalida(tmp_path):
    llm = FakeLLM()
    with pytest.raises(InvalidImageError):
        parse_contract_image(tmp_path / "nada.png", llm=llm)
    assert llm.messages is None  # validar antes de gastar: nunca se invoco al modelo


def test_wer_y_similitud():
    assert word_error_rate("a b c d", "a b c d") == 0.0
    assert word_error_rate("a b c d", "a x c") == pytest.approx(
        0.5
    )  # 1 sustitucion + 1 borrado
    assert word_error_rate("", "") == 0.0
    assert char_similarity("hola mundo", "hola  mundo") == 1.0
    assert char_similarity("USD 2.800", "USD 2.500") < 1.0
