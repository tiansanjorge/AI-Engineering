"""Punto de entrada: compara un contrato y su adenda (dos imagenes) y devuelve el JSON de cambios.

Flujo (cada etapa es un span hijo en Langfuse, bajo el span raiz `contract-analysis`):

    imagen original ─► parse_original_contract ─┐
                                                 ├─► contextualization_agent ─► extraction_agent ─► JSON
    imagen adenda   ─► parse_amendment_contract ─┘        (mapa contextual)       (cambios validados)

Uso (desde modulo-4/):
    python -m src.main data/test_contracts/par1_simple/original.png \\
                       data/test_contracts/par1_simple/adenda.png
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Permite tambien `python src/main.py ...`: agrega modulo-4/ al path para resolver `from src ...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import get_client, propagate_attributes

from src import config
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.errors import ContractAnalysisError
from src.image_parser import image_size, parse_contract_image, validate_image
from src.models import ContractChangeOutput, ExtractionResult
from src.observability import StageStats, flush, safe_trace_url, stage

TRACE_NAME = "contract-analysis"
TRACE_TAGS = ["modulo-4", "contract-comparison"]
RUNS_DIR = config.MODULE_ROOT / "outputs" / "runs"


@dataclass
class AnalysisResult:
    output: ContractChangeOutput
    stages: list[StageStats]
    trace_id: str | None
    trace_url: str | None
    # Detalle con el tipo de cada cambio (solo para evaluacion; no forma parte del contrato).
    detail: ExtractionResult | None = None


def _parse_stage(name: str, path: Path, parse_fn) -> tuple[str, StageStats]:
    """Etapa de parsing: una imagen -> su texto. Se usa dos veces (original y adenda)."""
    width, height = image_size(path)
    with stage(
        name,
        as_type="span",
        input={"image": path.name},
        run_name="vision_transcription",
        metadata={
            "model": config.VISION_MODEL,
            "image_kb": round(path.stat().st_size / 1024, 1),
            "image_px": f"{width}x{height}",
        },
    ) as st:
        text = parse_fn(path, run_config=st.config)
        st.set_output({"text": text, "chars": len(text)})
    return text, st.stats


def analyze_contracts(
    original_image: str | Path,
    amendment_image: str | Path,
    *,
    session_id: str | None = None,
    parse_fn=parse_contract_image,
    contextualizer: ContextualizationAgent | None = None,
    extractor: ExtractionAgent | None = None,
) -> AnalysisResult:
    """Ejecuta el pipeline completo. Las dependencias son inyectables para testear sin API."""
    # Falla rapido: se validan AMBAS imagenes antes de gastar tokens. Si la adenda estuviera
    # rota, no tendria sentido haber pagado antes la transcripcion del original.
    original, amendment = (
        validate_image(original_image),
        validate_image(amendment_image),
    )
    contextualizer = contextualizer or ContextualizationAgent()
    extractor = extractor or ExtractionAgent()

    langfuse = get_client()
    stats: list[StageStats] = []

    # Span raiz: su input/output pasan a ser el input/output del trace (legibles de un vistazo).
    with langfuse.start_as_current_observation(
        as_type="span",
        name=TRACE_NAME,
        input={"original": original.name, "amendment": amendment.name},
    ) as root:
        # Atributos que heredan TODOS los spans hijos (filtrables en el dashboard).
        with propagate_attributes(
            trace_name=TRACE_NAME,
            session_id=session_id,
            tags=TRACE_TAGS,
            metadata={
                "vision_model": config.VISION_MODEL,
                "agent_model": config.AGENT_MODEL,
            },
        ):
            try:
                original_text, s1 = _parse_stage(
                    "parse_original_contract", original, parse_fn
                )
                amendment_text, s2 = _parse_stage(
                    "parse_amendment_contract", amendment, parse_fn
                )

                # Agente 1 (analista): construye el mapa. Es el HANDOFF hacia el agente 2.
                with stage(
                    "contextualization_agent",
                    as_type="agent",
                    input={
                        "original_text": original_text,
                        "amendment_text": amendment_text,
                    },
                    run_name="context_map_generation",
                    metadata={"model": config.AGENT_MODEL, "role": "analista senior"},
                ) as st:
                    context_map = contextualizer.run(
                        original_text, amendment_text, st.config
                    )
                    st.set_output({"context_map": context_map})
                s3 = st.stats

                # Agente 2 (auditor): usa el mapa + ambos textos y devuelve el JSON validado.
                with stage(
                    "extraction_agent",
                    as_type="agent",
                    input={
                        "context_map": context_map,
                        "original_text": original_text,
                        "amendment_text": amendment_text,
                    },
                    run_name="structured_extraction",
                    metadata={"model": config.AGENT_MODEL, "role": "auditor"},
                ) as st:
                    output = extractor.run(
                        context_map, original_text, amendment_text, st.config
                    )
                    st.set_output(output.model_dump())
                    # Cuantos intentos hizo falta para pasar la validacion (1 = a la primera).
                    st.span.update(
                        metadata={
                            "model": config.AGENT_MODEL,
                            "role": "auditor",
                            "validation_attempts": extractor.last_attempts,
                        }
                    )
                s4 = st.stats
            except Exception as exc:
                root.update(
                    level="ERROR", status_message=f"{type(exc).__name__}: {exc}"
                )
                raise

        stats = [s1, s2, s3, s4]
        root.update(
            output=output.model_dump(),
            metadata={
                "total_tokens": sum(s.total_tokens for s in stats),
                "total_latency_s": round(sum(s.latency_s for s in stats), 3),
            },
        )
        trace_id = root.trace_id

    # Sin tracing (o sin claves validas) no hay URL: se degrada a None en vez de fallar.
    trace_url = safe_trace_url(trace_id)
    detail = getattr(extractor, "last_result", None)
    return AnalysisResult(output, stats, trace_id, trace_url, detail)


def _print_summary(result: AnalysisResult) -> None:
    """Resumen de etapas en stderr: stdout queda limpio para el JSON (se puede redirigir)."""
    err = sys.stderr
    print(
        "\nEtapa                       latencia   llamadas   tokens (in/out)", file=err
    )
    for s in result.stages:
        print(
            f"{s.name:27} {s.latency_s:7.1f}s   {s.llm_calls:^8}   "
            f"{s.total_tokens:>6} ({s.input_tokens}/{s.output_tokens})",
            file=err,
        )
    total = sum(s.total_tokens for s in result.stages)
    print(
        f"{'TOTAL':27} {sum(s.latency_s for s in result.stages):7.1f}s   {'':8}   {total:>6}",
        file=err,
    )
    if result.trace_url:
        print(f"\nTraza en Langfuse: {result.trace_url}", file=err)


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(
        description="Compara un contrato y su adenda (imagenes)."
    )
    cli.add_argument("original", help="imagen del contrato original (PNG/JPEG)")
    cli.add_argument("amendment", help="imagen de la adenda (PNG/JPEG)")
    cli.add_argument("--output", help="donde guardar el JSON (default: outputs/runs/)")
    cli.add_argument(
        "--session-id", help="agrupa varias corridas en una sesion de Langfuse"
    )
    args = cli.parse_args(argv)

    # La consola de Windows usa cp1252 por defecto y rompe los acentos del JSON.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    try:
        config.require_openai_key()
        result = analyze_contracts(
            args.original, args.amendment, session_id=args.session_id
        )
    except ContractAnalysisError as exc:
        # Falla controlada: mensaje claro y codigo de salida distinto de 0 (sin traceback).
        print(f"ERROR [{type(exc).__name__}]: {exc}", file=sys.stderr)
        return 1
    finally:
        flush()  # tambien ante errores: la traza del fallo debe llegar a Langfuse

    payload = json.dumps(result.output.model_dump(), ensure_ascii=False, indent=2)
    print(payload)

    out_path = (
        Path(args.output)
        if args.output
        else RUNS_DIR
        / (f"{datetime.now():%Y%m%d_%H%M%S}_{Path(args.original).parent.name}.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"\nJSON guardado en {out_path}", file=sys.stderr)
    _print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
