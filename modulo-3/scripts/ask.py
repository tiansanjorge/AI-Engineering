"""Hace una consulta al sistema multi-agente completo y muestra el resultado como JSON.

Uso (desde modulo-3/):  python scripts/ask.py "¿Cuántos días de vacaciones me tocan?" [--trace]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.multi_agent_system import answer_query


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta al sistema multi-agente")
    parser.add_argument("question")
    parser.add_argument(
        "--trace", action="store_true", help="Registrar la consulta en Langfuse"
    )
    args = parser.parse_args()
    if args.trace:
        from src.observability import flush, traced_query

        traced = traced_query(args.question, user_id="cli-user", session_id="cli")
        flush()
        print(json.dumps(traced.result.model_dump(), ensure_ascii=False, indent=2))
        print(f"Trace: {traced.trace_url}")
    else:
        print(
            json.dumps(
                answer_query(args.question).model_dump(), ensure_ascii=False, indent=2
            )
        )


if __name__ == "__main__":
    main()
