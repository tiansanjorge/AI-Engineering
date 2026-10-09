"""Corre un agente RAG sobre una pregunta y muestra el resultado como JSON.

Uso (desde modulo-3/):
    python scripts/run_agent.py hr "¿Cuántos días de vacaciones me tocan?"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.registry import build_agents
from src.config import DOMAINS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consulta a un agente RAG especializado"
    )
    parser.add_argument("domain", choices=sorted(DOMAINS))
    parser.add_argument("question")
    args = parser.parse_args()
    result = build_agents()[args.domain].answer(args.question)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
