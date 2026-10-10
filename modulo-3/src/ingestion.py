"""Carga de documentos y chunking por estructura.

Estrategia (decision tomada a partir del feedback del Modulo 2, que marcaba que cortar por
cantidad fija de tokens puede partir oraciones):

- `.md`  -> una seccion `##` = un chunk.
- `.csv` -> una fila = un chunk.
- `.txt` -> un parrafo (encabezado + cuerpo) = un chunk.
- Si una unidad supera `MAX_CHUNK_TOKENS`, se corta por limites de oracion con una oracion de
  solapamiento (nunca a mitad de palabra).

Cada chunk lleva metadatos (dominio, fuente, documento, seccion, formato) que habilitan filtros
de recuperacion y que se usan para citar fuentes en las respuestas.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import tiktoken
from langchain_core.documents import Document

from src.config import DATA_DIR, DOMAINS, MAX_CHUNK_TOKENS

_ENCODING = tiktoken.get_encoding("cl100k_base")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_SUPPORTED = {".md", ".csv", ".txt"}


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


@dataclass(frozen=True)
class Unit:
    """Una unidad estructural del documento: un encabezado y su cuerpo."""

    section: str
    body: str


def _markdown_units(text: str) -> tuple[str, list[Unit]]:
    title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    # parts = [preambulo, titulo1, cuerpo1, titulo2, cuerpo2, ...]
    units = [
        Unit(section=parts[i].strip(), body=parts[i + 1].strip())
        for i in range(1, len(parts) - 1, 2)
        if parts[i + 1].strip()
    ]
    return title, units


def _csv_units(path: Path) -> tuple[str, list[Unit]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    first_column = next(iter(rows[0]))
    units = [
        Unit(
            section=row[first_column].strip(),
            body="; ".join(
                f"{k}: {v.strip()}" for k, v in row.items() if k != first_column
            ),
        )
        for row in rows
    ]
    return path.stem.replace("_", " "), units


def _text_units(text: str) -> tuple[str, list[Unit]]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    title = blocks[0].splitlines()[0].strip()
    units = []
    for block in blocks[1:]:
        lines = [line.strip() for line in block.splitlines()]
        if len(lines) > 1:
            units.append(Unit(section=lines[0], body=" ".join(lines[1:])))
    return title, units


def split_long_text(text: str, max_tokens: int = MAX_CHUNK_TOKENS) -> list[str]:
    """Parte un texto en trozos de a lo sumo `max_tokens`, cortando en limites de oracion.

    La ultima oracion de cada trozo se repite al inicio del siguiente (solapamiento) para no
    perder el hilo entre trozos. Una oracion que por si sola excede el tope se corta por palabras.
    """
    if count_tokens(text) <= max_tokens:
        return [text]
    sentences: list[str] = []
    for sentence in _SENTENCE_BOUNDARY.split(text):
        if count_tokens(sentence) <= max_tokens:
            sentences.append(sentence)
            continue
        words, current = sentence.split(), []
        for word in words:
            if current and count_tokens(" ".join([*current, word])) > max_tokens:
                sentences.append(" ".join(current))
                current = []
            current.append(word)
        if current:
            sentences.append(" ".join(current))

    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if current and count_tokens(" ".join([*current, sentence])) > max_tokens:
            chunks.append(" ".join(current))
            current = [
                current[-1]
            ]  # solapamiento: la ultima oracion del trozo anterior
            if count_tokens(" ".join([*current, sentence])) > max_tokens:
                current = []
        current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    return chunks


def load_file(path: Path, domain: str) -> list[Document]:
    """Convierte un archivo en chunks con metadatos."""
    if path.suffix == ".md":
        doc_title, units = _markdown_units(path.read_text(encoding="utf-8"))
    elif path.suffix == ".csv":
        doc_title, units = _csv_units(path)
    elif path.suffix == ".txt":
        doc_title, units = _text_units(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")

    documents: list[Document] = []
    for unit in units:
        # El titulo del documento y la seccion forman parte del texto indexado: dan contexto al
        # embedding y al LLM (un parrafo aislado como "Se paga el ultimo dia habil" no dice de que habla).
        header = f"{doc_title} - {unit.section}"
        parts = split_long_text(f"{header}\n{unit.body}")
        for part_number, content in enumerate(parts, start=1):
            chunk_number = len(documents) + 1
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "chunk_id": f"{domain}:{path.stem}:{chunk_number:03d}",
                        "domain": domain,
                        "source": f"{DOMAINS[domain]}/{path.name}",
                        "doc_title": doc_title,
                        "section": unit.section,
                        "format": path.suffix.lstrip("."),
                        "part": f"{part_number}/{len(parts)}",
                        "tokens": count_tokens(content),
                    },
                )
            )
    return documents


def load_domain(domain: str, data_dir: Path = DATA_DIR) -> list[Document]:
    """Todos los chunks de un dominio, en orden estable (por nombre de archivo)."""
    if domain not in DOMAINS:
        raise ValueError(f"Dominio desconocido: {domain!r}. Validos: {sorted(DOMAINS)}")
    folder = data_dir / DOMAINS[domain]
    files = sorted(p for p in folder.iterdir() if p.suffix in _SUPPORTED)
    if not files:
        raise FileNotFoundError(f"No hay documentos en {folder}")
    documents: list[Document] = []
    for path in files:
        documents.extend(load_file(path, domain))
    return documents
