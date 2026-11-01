"""Genera los contratos de prueba (imagenes) y su ground truth (`expected.json`).

Por que generarlos por script: el texto correcto se conoce de antemano, asi que despues se puede
MEDIR el parsing de vision (fidelidad del texto) y la extraccion (cambios detectados) en vez de
juzgar a ojo. El script es determinista (misma semilla) y reproducible.

Salida en data/test_contracts/:
    par1_simple/                original.png, adenda.png, expected.json
    par2_complejo/              original.png, adenda.png, expected.json
    par3_escaneo_degradado/     original.jpg, adenda.jpg, expected.json  (par 1 + escaneo malo)

Uso (desde modulo-4/):  python scripts/generate_contracts.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract_specs as specs
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from src import config

PAGE_W, PAGE_H = 1240, 1754  # A4 a 150 dpi
MARGIN = 110
FONT_DIR = Path("C:/Windows/Fonts")
SEED = 42


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Tipografia serif (aspecto legal); si no esta disponible, la fuente por defecto de Pillow."""
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


def wrap(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Corte de linea por palabras segun el ancho real en pixeles."""
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(blocks: list[specs.Block]) -> Image.Image:
    """Dibuja una pagina limpia: titulo centrado, encabezados en negrita, incisos con sangria."""
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(img)
    body = load_font("times.ttf", 27)
    bold = load_font("timesbd.ttf", 27)
    title = load_font("timesbd.ttf", 32)
    width = PAGE_W - 2 * MARGIN
    y = MARGIN

    for kind, text in blocks:
        if kind == "title":
            for line in wrap(text, title, width, draw):
                x = (PAGE_W - draw.textlength(line, font=title)) / 2
                draw.text((x, y), line, font=title, fill="black")
                y += 44
            y += 24
        elif kind == "heading":
            y += 8
            draw.text((MARGIN, y), text, font=bold, fill="black")
            y += 38
        elif kind in ("para", "sub"):
            indent = 50 if kind == "sub" else 0
            for line in wrap(text, body, width - indent, draw):
                draw.text((MARGIN + indent, y), line, font=body, fill="black")
                y += 36
            y += 8
        elif kind == "sign":
            y += 70
            draw.text((MARGIN, y), text, font=body, fill="black")
            y += 40

    assert y < PAGE_H - MARGIN, f"El contenido no entra en una pagina (y={y})"
    return img


def degrade(img: Image.Image) -> Image.Image:
    """Simula un escaneo malo: leve rotacion, fondo grisaceo, ruido de sensor y desenfoque."""
    rng = random.Random(SEED)
    rotated = img.rotate(
        rng.choice([-1, 1]) * 2.2,
        resample=Image.BICUBIC,
        expand=True,
        fillcolor=(226, 226, 222),
    )
    # Fondo ligeramente gris (papel viejo) y texto menos contrastado.
    gray = Image.new("RGB", rotated.size, (232, 230, 224))
    paper = ImageChops.multiply(rotated, gray)
    # Ruido gaussiano de sensor mezclado con la imagen.
    noise = Image.effect_noise(paper.size, 22).convert("RGB")
    noisy = Image.blend(paper, ImageChops.multiply(paper, noise), 0.35)
    return noisy.filter(ImageFilter.GaussianBlur(1.1))


def write_pair(
    folder: Path, original, amendment, expected: dict, ext: str, scan: bool
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    texts = {}
    for name, blocks in (("original", original), ("adenda", amendment)):
        img = render(blocks)
        if scan:
            img = degrade(img)
        path = folder / f"{name}.{ext}"
        # JPEG con calidad media: otro artefacto tipico de un escaneo real.
        img.save(path, quality=62) if ext == "jpg" else img.save(path)
        texts[name] = "\n".join(text for _, text in blocks)
    ground_truth = {
        **expected,
        "images": {"original": f"original.{ext}", "amendment": f"adenda.{ext}"},
        "documents": {"original": texts["original"], "amendment": texts["adenda"]},
    }
    (folder / "expected.json").write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] {folder.name}")


def main() -> None:
    out = config.TEST_CONTRACTS_DIR
    write_pair(
        out / "par1_simple",
        specs.SIMPLE_ORIGINAL,
        specs.SIMPLE_AMENDMENT,
        specs.SIMPLE_EXPECTED,
        "png",
        scan=False,
    )
    write_pair(
        out / "par2_complejo",
        specs.COMPLEX_ORIGINAL,
        specs.COMPLEX_AMENDMENT,
        specs.COMPLEX_EXPECTED,
        "png",
        scan=False,
    )
    # Par 3: mismo contenido y mismo ground truth que el par 1, pero con escaneo degradado.
    degraded = {
        **specs.SIMPLE_EXPECTED,
        "case_id": "par3_escaneo_degradado",
        "description": "Mismo contenido que el par 1, con imagen degradada (rotada, ruido, JPEG).",
    }
    write_pair(
        out / "par3_escaneo_degradado",
        specs.SIMPLE_ORIGINAL,
        specs.SIMPLE_AMENDMENT,
        degraded,
        "jpg",
        scan=True,
    )


if __name__ == "__main__":
    main()
