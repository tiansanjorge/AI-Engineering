"""Hace una consulta al sistema multi-agente completo y muestra el resultado como JSON.

Uso (desde modulo-3/):  python scripts/ask.py "¿Cuántos días de vacaciones me tocan?"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.multi_agent_system import answer_query  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta al sistema multi-agente")
    parser.add_argument("question")
    args = parser.parse_args()
    print(json.dumps(answer_query(args.question).model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
