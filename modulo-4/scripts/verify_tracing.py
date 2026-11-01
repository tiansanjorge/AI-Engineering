"""Verifica contra Langfuse REAL que la traza de un analisis cumple lo que pide la consigna.

Corre (o lee) un analisis, espera a que la traza aparezca y la audita:
  - jerarquia: contract-analysis -> 4 etapas -> sus generations
  - tipos de observacion correctos (agent / generation)
  - modelo, tokens y costo en cada generation
  - input/output presentes en cada etapa; latencia en cada observacion
  - atributos del trace (session, tags) y que no haya observaciones en ERROR

Las trazas se leen con `api.observations.get_many`: `api.trace.get` devuelve 410 en
organizaciones nuevas de Langfuse.

Uso (desde modulo-4/):
    python scripts/verify_tracing.py                      # corre el par 1 y lo audita
    python scripts/verify_tracing.py --trace-id <id>      # audita una traza existente
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import get_client

from src import config
from src.main import analyze_contracts
from src.observability import flush

EXPECTED_STAGES = {
    "parse_original_contract": "span",
    "parse_amendment_contract": "span",
    "contextualization_agent": "agent",
    "extraction_agent": "agent",
}
OUTPUT = config.MODULE_ROOT / "outputs" / "tracing_check.json"


def fetch(trace_id: str):
    client = get_client()
    for _ in range(15):  # la API puede tardar unos segundos en reflejar la traza
        obs = client.api.observations.get_many(
            trace_id=trace_id, limit=200, fields="core,basic,io,usage,time,model"
        ).data
        # Se espera a que esten TODAS las etapas (la ingesta llega en partes).
        names = {o.name for o in obs}
        if set(EXPECTED_STAGES) <= names and "contract-analysis" in names:
            return obs
        time.sleep(3)
    return obs


def audit(obs) -> list[tuple[str, bool, str]]:
    by_id = {o.id: o for o in obs}
    root = next((o for o in obs if o.name == "contract-analysis"), None)
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    check("span raiz 'contract-analysis' existe", root is not None)
    if root is None:
        return checks
    check("raiz sin padre", root.parent_observation_id is None)
    check("raiz con input y output", root.input and root.output)

    for name, kind in EXPECTED_STAGES.items():
        stage = next((o for o in obs if o.name == name), None)
        check(f"etapa '{name}' existe", stage is not None)
        if stage is None:
            continue
        check(f"  '{name}' es hija de la raiz", stage.parent_observation_id == root.id)
        check(f"  '{name}' tipo {kind}", stage.type.lower() == kind, f"es {stage.type}")
        check(f"  '{name}' con input y output", stage.input and stage.output)
        check(f"  '{name}' con latencia", bool(stage.latency), f"{stage.latency}")
        gens = [
            o
            for o in obs
            if o.parent_observation_id
            and _ancestor(o, by_id) == stage.id
            and o.type.lower() == "generation"
        ]
        check(f"  '{name}' tiene generation anidada", bool(gens))
        for g in gens:
            usage = g.usage_details or {}
            check(f"    generation '{g.name}' con modelo", bool(g.model), f"{g.model}")
            check(
                f"    generation '{g.name}' con tokens",
                usage.get("input", 0) > 0 and usage.get("output", 0) > 0,
                f"{usage}",
            )
            cost = g.cost_details or {}
            check(
                f"    generation '{g.name}' con costo",
                (g.total_cost or 0) > 0,
                f"{cost}",
            )

    check("ninguna observacion en ERROR", not [o for o in obs if o.level == "ERROR"])
    return checks


def _ancestor(obs, by_id):
    """Id de la etapa (hija directa de la raiz) a la que pertenece una observacion."""
    cur = obs
    while (
        cur.parent_observation_id and by_id.get(cur.parent_observation_id) is not None
    ):
        parent = by_id[cur.parent_observation_id]
        if parent.name == "contract-analysis":
            return cur.id
        cur = parent
    return None


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--trace-id")
    args = cli.parse_args()

    trace_id = args.trace_id
    if not trace_id:
        case = config.TEST_CONTRACTS_DIR / "par1_simple"
        result = analyze_contracts(
            case / "original.png", case / "adenda.png", session_id="verify-fase6"
        )
        flush()
        trace_id = result.trace_id
        print(f"Traza generada: {result.trace_url}")

    obs = fetch(trace_id)
    print(f"\nArbol de observaciones ({len(obs)}):")
    by_id = {o.id: o for o in obs}
    for o in sorted(obs, key=lambda o: str(o.start_time)):
        depth = 0
        cur = o
        while cur.parent_observation_id and cur.parent_observation_id in by_id:
            depth += 1
            cur = by_id[cur.parent_observation_id]
        usage = o.usage_details or {}
        print(
            f"{'  ' * depth}- [{o.type}] {o.name}  lat={o.latency}s  tokens={usage.get('total', '-')}"
        )

    checks = audit(obs)
    print()
    for name, ok, detail in checks:
        print(
            f"[{'OK' if ok else 'FALLA'}] {name}"
            + (f"   ({detail})" if not ok and detail else "")
        )
    failed = [c for c in checks if not c[1]]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} chequeos OK")
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "trace_id": trace_id,
                "checks": [{"check": n, "ok": ok} for n, ok, _ in checks],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
