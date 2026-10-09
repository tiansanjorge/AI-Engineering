"""Tests de carga de documentos y chunking. No llaman a ninguna API."""

import itertools

import pytest

from src.config import DOMAINS, MAX_CHUNK_TOKENS
from src.ingestion import count_tokens, load_domain, load_file, split_long_text

REQUIRED_METADATA = {
    "chunk_id",
    "domain",
    "source",
    "doc_title",
    "section",
    "format",
    "part",
    "tokens",
}


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_each_domain_has_at_least_50_chunks(domain):
    assert len(load_domain(domain)) >= 50


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_chunks_have_metadata_and_unique_ids(domain):
    docs = load_domain(domain)
    ids = [d.metadata["chunk_id"] for d in docs]
    assert len(ids) == len(set(ids))
    for d in docs:
        assert REQUIRED_METADATA <= d.metadata.keys()
        assert d.metadata["domain"] == domain
        assert d.metadata["source"].startswith(DOMAINS[domain])
        assert d.page_content.strip()


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_chunks_respect_token_cap(domain):
    for d in load_domain(domain):
        assert d.metadata["tokens"] == count_tokens(d.page_content)
        assert d.metadata["tokens"] <= MAX_CHUNK_TOKENS


@pytest.mark.parametrize("domain", sorted(DOMAINS))
def test_domain_mixes_all_three_formats(domain):
    assert {d.metadata["format"] for d in load_domain(domain)} == {"md", "csv", "txt"}


def test_chunk_text_carries_document_title_and_section():
    chunk = load_domain("hr")[0]
    assert chunk.page_content.startswith(
        f"{chunk.metadata['doc_title']} - {chunk.metadata['section']}"
    )


def test_markdown_one_section_is_one_chunk(tmp_path):

    path = tmp_path / "doc.md"
    path.write_text(
        "# Titulo\n\nintro\n\n## A\ncuerpo a\n\n## B\ncuerpo b\n", encoding="utf-8"
    )
    docs = load_file(path, "hr")
    assert [d.metadata["section"] for d in docs] == ["A", "B"]
    assert docs[0].page_content == "Titulo - A\ncuerpo a"


def test_csv_one_row_is_one_chunk(tmp_path):
    path = tmp_path / "faq.csv"
    path.write_text(
        'id,pregunta,respuesta\nQ1,"¿Hola, qué tal?",Bien\nQ2,Otra,Ok\n',
        encoding="utf-8",
    )
    docs = load_file(path, "tech")
    assert len(docs) == 2
    assert docs[0].metadata["section"] == "Q1"
    assert "pregunta: ¿Hola, qué tal?" in docs[0].page_content


def test_txt_paragraphs_skip_title_block(tmp_path):
    path = tmp_path / "nota.txt"
    path.write_text(
        "Titulo\nnota\n\nEncabezado uno\nCuerpo uno.\n\nEncabezado dos\nCuerpo dos.\n",
        encoding="utf-8",
    )
    docs = load_file(path, "finance")
    assert [d.metadata["section"] for d in docs] == ["Encabezado uno", "Encabezado dos"]


def test_unsupported_format_and_unknown_domain():
    with pytest.raises(ValueError):
        load_domain("legal")


def test_long_text_splits_on_sentence_boundaries_with_overlap():
    sentences = [
        f"Esta es la oracion numero {i} con algunas palabras de relleno."
        for i in range(40)
    ]
    text = " ".join(sentences)
    parts = split_long_text(text, max_tokens=80)
    assert len(parts) > 1
    for part in parts:
        assert count_tokens(part) <= 80
        assert part.endswith(".")  # nunca se corta a mitad de oracion
    # solapamiento: la ultima oracion de un trozo abre el siguiente
    for a, b in itertools.pairwise(parts):
        assert a.split(". ")[-1].rstrip(".") in b


def test_short_text_is_not_split():
    assert split_long_text("Una sola oracion corta.") == ["Una sola oracion corta."]


def test_single_giant_sentence_is_cut_by_words():
    text = " ".join(["palabra"] * 500)
    parts = split_long_text(text, max_tokens=50)
    assert all(count_tokens(p) <= 50 for p in parts)
    assert sum(len(p.split()) for p in parts) == 500
