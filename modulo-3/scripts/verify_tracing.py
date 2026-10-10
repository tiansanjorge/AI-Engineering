"""Verifica contra Langfuse el checklist de observabilidad del PI (lecture 4).

Ejecuta 3 consultas reales (con respuesta, con nota de otra area y fuera de alcance), espera a
que los traces sean legibles por API y comprueba:
  1. Cada request genera exactamente un trace (un unico span raiz `support-request`).
  2. El router tiene su propio span (`orchestrator-routing`) con input y output.
  3. El agente que atiende tiene su span (`<dominio>-agent`) con input y output
     (y una consulta fuera de alcance NO invoca ningun agente).
  4. Las llamadas al LLM aparecen como GENERATION dentro de sus spans.
  5. Hay metadata para filtrar por usuario y sesion, y el score `routed_intent` por intencion.
  6. Los scores (`routed_intent`, `routing_correct`) quedan asociados al trace correcto, con su valor.
Guarda la evidencia en outputs/tracing_check.json. Llama a la API (centavos).

Uso (desde modulo-3/):  python scripts/verify_tracing.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import get_client

from src.config import MODULE_ROOT
from src.observability import flush, traced_query

CASES = [
    ("hr", "¿Cuántos días de vacaciones me tocan si llevo 4 años?"),
    ("tech", "No puedo entrar a Nimbus Expenses para cargar un gasto"),
    ("out_of_scope", "¿Quién ganó el mundial de fútbol de 2014?"),
]
RUN_TAG = "tracing-check"


def fetch_observations(client, trace_id: str, minimum: int, timeout: int = 90):
    deadline = time.time() + timeout
    obs = []
    while time.time() < deadline:
        obs = client.api.observations.get_many(
            trace_id=trace_id, limit=100, fields="core,basic,io,usage,time"
        ).data
        if len(obs) >= minimum:
            return obs
        time.sleep(4)
    return obs


def fetch_scores(client, trace_id: str, expected: set[str], timeout: int = 60):
    deadline = time.time() + timeout
    scores = []
    while time.time() < deadline:
        scores = client.api.scores_v3.get_many_v3(trace_id=trace_id, limit=50).data
        if expected <= {s.name for s in scores}:
            return scores
        time.sleep(4)
    return scores


def ancestors(obs_by_id: dict, obs) -> list[str]:
    chain, current = [], obs
    while current is not None and current.parent_observation_id:
        current = obs_by_id.get(current.parent_observation_id)
        if current is not None:
            chain.append(current.name)
    return chain


def check_case(client, expected: str, question: str) -> dict:
    traced = traced_query(
        question,
        user_id="verify-user",
        session_id=f"verify-session-{expected}",
        tags=[RUN_TAG],
        expected_intent=expected,
    )
    flush()
    result, trace_id = traced.result, traced.trace_id
    obs = fetch_observations(
        client, trace_id, minimum=6 if expected == "out_of_scope" else 12
    )
    by_id = {o.id: o for o in obs}
    names = [o.name for o in obs]
    roots = [o for o in obs if o.is_root_observation]
    router = next((o for o in obs if o.name == "orchestrator-routing"), None)
    agents = [o for o in obs if o.name.endswith("-agent")]
    generations = [o for o in obs if o.type == "GENERATION"]
    scores = fetch_scores(client, trace_id, {"routed_intent", "routing_correct"})
    by_score = {s.name: s.value for s in scores}

    checks = {
        "1_un_solo_trace_un_span_raiz": len({o.trace_id for o in obs}) == 1
        and len(roots) == 1
        and roots[0].name == "support-request",
        "2_router_con_span_input_output": router is not None
        and router.input is not None
        and router.output is not None,
        "3_agente_con_span_input_output": (
            not agents
            if expected == "out_of_scope"
            else len(agents) == 1
            and agents[0].name == f"{result.intent}-agent"
            and agents[0].input is not None
            and agents[0].output is not None
        ),
        "4_generations_dentro_de_sus_spans": bool(generations)
        and any("orchestrator-routing" in ancestors(by_id, g) for g in generations)
        and (
            expected == "out_of_scope"
            or any(f"{result.intent}-agent" in ancestors(by_id, g) for g in generations)
        ),
        "5_metadata_usuario_sesion": all(
            o.user_id == "verify-user" and o.session_id == f"verify-session-{expected}"
            for o in obs
        ),
        # Los scores se consultan filtrando por este trace_id: si aparecen, estan asociados a el.
        "6_scores_en_el_trace_correcto": by_score.get("routed_intent")
        == (result.intent or "error")
        and by_score.get("routing_correct") == (result.intent == expected),
    }
    return {
        "expected_intent": expected,
        "routed_intent": result.intent,
        "question": question,
        "trace_id": trace_id,
        "trace_url": traced.trace_url,
        "observations": len(obs),
        "spans": sorted(set(names)),
        "scores": by_score,
        "checks": checks,
    }


def main() -> None:
    client = get_client()
    assert client.auth_check(), "Credenciales de Langfuse invalidas"
    report = [check_case(client, expected, question) for expected, question in CASES]
    out = MODULE_ROOT / "outputs" / "tracing_check.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = 0
    for row in report:
        print(
            f"\n{row['expected_intent']:13} -> {row['routed_intent']}  ({row['observations']} observaciones)"
        )
        print(f"  {row['trace_url']}")
        for name, ok in row["checks"].items():
            print(f"  [{'OK' if ok else 'FALLA'}] {name}")
            failed += not ok
    print(
        f"\nChecklist: {'COMPLETO' if not failed else f'{failed} verificaciones fallaron'}"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
