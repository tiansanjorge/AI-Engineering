"""Construye los agentes especializados y los expone por nombre de dominio."""

from langchain_core.language_models import BaseChatModel

from src.agents.finance_agent import build_finance_agent
from src.agents.hr_agent import build_hr_agent
from src.agents.rag_agent import RAGAgent, default_llm
from src.agents.tech_agent import build_tech_agent


def build_agents(
    llm: BaseChatModel | None = None, **retriever_kwargs
) -> dict[str, RAGAgent]:
    """Un agente por dominio, compartiendo el mismo LLM (se crea uno si no se pasa)."""
    llm = llm or default_llm()
    return {
        "hr": build_hr_agent(llm, **retriever_kwargs),
        "tech": build_tech_agent(llm, **retriever_kwargs),
        "finance": build_finance_agent(llm, **retriever_kwargs),
    }
