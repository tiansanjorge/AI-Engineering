"""Estadisticas del corpus: unidades (secciones .md, filas .csv, parrafos .txt) y tokens.

Sirve para comprobar el requisito de la consigna (>= 50 chunks por dominio) antes de
construir los indices. La unidad es una aproximacion del chunking por estructura.

Uso (desde modulo-3/):  python scripts/corpus_stats.py
"""

import csv
import re
import sys
from pathlib import Path

import tiktoken

DATA = Path(__file__).resolve().parent.parent / "data"
DOMAINS = ["hr_docs", "tech_docs", "finance_docs"]
ENC = tiktoken.get_encoding("cl100k_base")


def units(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        parts = re.split(r"^## ", text, flags=re.M)[1:]
        return [p.strip() for p in parts]
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        header, body = rows[0], rows[1:]
        bad = [i + 2 for i, r in enumerate(body) if len(r) != len(header)]
        if bad:
            print(f"  [ERROR] {path.name}: filas con columnas != {len(header)}: lineas {bad}")
            sys.exit(1)
        return [" | ".join(r) for r in body]
    return [p.strip() for p in re.split(r"\n\s*\n", text)[1:] if p.strip()]


def main() -> None:
    for domain in DOMAINS:
        total = 0
        print(domain)
        for path in sorted((DATA / domain).glob("*")):
            us = units(path)
            toks = [len(ENC.encode(u)) for u in us]
            total += len(us)
            print(
                f"  {path.name:48} unidades={len(us):3} tokens min/med/max="
                f"{min(toks)}/{sum(toks) // len(toks)}/{max(toks)}"
            )
        print(f"  => {total} unidades ({'OK' if total >= 50 else 'INSUFICIENTE'} vs minimo 50)\n")


if __name__ == "__main__":
    main()
