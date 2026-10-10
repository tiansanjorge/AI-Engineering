"""Punto de entrada del sistema multi-agente.

    from src.multi_agent_system import answer_query
    resultado = answer_query("¿Cuántos días de vacaciones me tocan?")

Es la unica funcion que necesita conocer quien consuma el sistema (notebook, CLI o, mas adelante,
una API HTTP): la construccion de agentes, retrievers y grafo queda encapsulada aca.
"""

from functools import lru_cache

from langchain_core.runnables import RunnableConfig

from src.agents.orchestrator import Orchestrator, OrchestratorResult


@lru_cache(maxsize=1)
def get_system() -> Orchestrator:
    """Sistema por defecto (se construye una sola vez por proceso)."""
    return Orchestrator()


def answer_query(
    question: str, config: RunnableConfig | None = None
) -> OrchestratorResult:
    return get_system().run(question, config)
