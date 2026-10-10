"""Configuracion central del modulo: rutas, dominios y modelos.

Los modelos se leen de variables de entorno (con el mismo default que M1/M2) para poder
cambiarlos sin tocar codigo.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Busca el .env subiendo por los directorios padres (el .env compartido vive en la raiz del repo).
load_dotenv()

MODULE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = MODULE_ROOT / "data"
CHROMA_DIR = MODULE_ROOT / "chroma_db"

# Dominio -> carpeta de documentos. Cada dominio tiene su propia coleccion y su propio agente.
DOMAINS: dict[str, str] = {
    "hr": "hr_docs",
    "tech": "tech_docs",
    "finance": "finance_docs",
}

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Precio de embeddings (USD por millon de tokens) para estimar el costo de indexar.
EMBEDDING_PRICE_PER_M_TOKENS = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
}

# Tope de tokens por chunk. Las secciones del corpus miden ~80 tokens, asi que casi nunca se
# activa: es un seguro para documentos futuros mas largos (se corta por oraciones, con solapamiento).
MAX_CHUNK_TOKENS = 300

# Recuperacion por defecto (cuantos chunks recibe el LLM como contexto).
DEFAULT_K = 4
