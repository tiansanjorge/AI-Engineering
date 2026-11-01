"""Prueba de humo del entorno del Modulo 4.

Verifica, con llamadas reales y de costo despreciable:
  1. Langfuse: credenciales/region validas y que el proyecto sea el NUEVO (sin trazas previas).
  2. Vision: el modelo configurado lee una imagen generada en memoria (base64, como en produccion).
  3. Trazabilidad: la llamada queda registrada en Langfuse y se puede leer de vuelta.

Uso (desde modulo-4/):  python scripts/smoke_test.py
"""

import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from PIL import Image, ImageDraw

from src import config

MARKER = "CLAUSULA SEGUNDA: 1500 USD"


def check_langfuse(client) -> None:
    assert client.auth_check(), (
        "Langfuse rechazo las credenciales (revisar claves y region)"
    )
    # Si ya hay observaciones, el proyecto no es nuevo: avisamos (no es un error, es un dato).
    previas = client.api.observations.get_many(limit=1).data
    estado = (
        "VACIO (proyecto nuevo)"
        if not previas
        else "CON TRAZAS PREVIAS (revisar si es el proyecto correcto)"
    )
    print(f"[ok] Langfuse auth. Proyecto: {estado}")


def make_test_image() -> str:
    """Dibuja una linea de texto y la devuelve en base64: mismo formato que usara el parser real."""
    img = Image.new("RGB", (700, 120), "white")
    ImageDraw.Draw(img).text((20, 45), MARKER, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def check_vision_traced(client) -> None:
    handler = CallbackHandler()
    llm = ChatOpenAI(
        model=config.VISION_MODEL, temperature=0, timeout=config.REQUEST_TIMEOUT_S
    )
    msg = HumanMessage(
        content=[
            {"type": "text", "text": "Transcribe exactamente el texto de la imagen."},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{make_test_image()}"},
            },
        ]
    )
    out = llm.invoke([msg], config={"callbacks": [handler]})
    print(f"[ok] Vision ({config.VISION_MODEL}) leyo: {out.content!r}")
    assert "1500" in out.content, "La vision no leyo el monto: revisar el modelo"

    client.flush()
    trace_id = handler.last_trace_id
    # api.trace.get devuelve 410 en organizaciones nuevas: se lee por observaciones.
    for _ in range(10):
        obs = client.api.observations.get_many(trace_id=trace_id, limit=20).data
        if obs:
            print(f"[ok] Trace leido de vuelta ({sorted({o.name for o in obs})})")
            return
        time.sleep(3)
    raise AssertionError("El trace no aparecio en Langfuse tras 30s")


if __name__ == "__main__":
    lf = get_client()
    check_langfuse(lf)
    check_vision_traced(lf)
    print("Smoke test completo.")
