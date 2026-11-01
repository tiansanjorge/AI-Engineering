"""Configuracion central del modulo: rutas, modelos y limites.

Todo lo que podria cambiar entre entornos (modelos, timeouts) se lee de variables de entorno con
un default razonable. Las credenciales NUNCA viven en el codigo: solo en el `.env`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.errors import ConfigError

# Busca el .env subiendo por los directorios padres (el .env compartido vive en la raiz del repo).
load_dotenv()

MODULE_ROOT = Path(__file__).resolve().parent.parent
TEST_CONTRACTS_DIR = MODULE_ROOT / "data" / "test_contracts"

# La consigna pide GPT-4o para la vision. Los agentes usan el mismo por precision en texto legal;
# se separan en dos variables para poder abaratar uno sin tocar el otro.
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o")

# Robustez frente a la API: un timeout evita colgarse; los reintentos cubren fallos transitorios
# (rate limit, 5xx) sin que el pipeline entero falle por un hipo de red.
REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "120"))
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "3"))

# Validacion de entrada: solo estos formatos y este tamano maximo se mandan al modelo.
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_IMAGE_MB = 20

# Cuantas veces se le devuelve al agente extractor su propio error de validacion para que lo
# corrija (self-healing). Con 0 el primer fallo de formato ya seria definitivo.
MAX_VALIDATION_RETRIES = int(os.getenv("MAX_VALIDATION_RETRIES", "2"))


def require_openai_key() -> None:
    """Falla temprano y con un mensaje claro si falta la clave, en vez de un error opaco de la API."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigError(
            "Falta OPENAI_API_KEY. Copia .env.example a .env y completalo (o definila como "
            "variable de entorno)."
        )


# Tope de tokens de SALIDA por etapa. Acota el costo y el tiempo ante una salida desbocada (el
# modelo que no termina de generar). Una transcripcion o un mapa de una pagina rondan los
# 450-650 tokens y una extraccion los 250-400; los topes dejan un margen amplio. Un documento de
# varias paginas necesitaria subirlos (hoy una imagen por documento).
VISION_MAX_TOKENS = int(os.getenv("VISION_MAX_TOKENS", "4096"))
CONTEXT_MAX_TOKENS = int(os.getenv("CONTEXT_MAX_TOKENS", "4096"))
EXTRACTION_MAX_TOKENS = int(os.getenv("EXTRACTION_MAX_TOKENS", "2048"))
