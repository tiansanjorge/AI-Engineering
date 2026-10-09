"""Agente de Recursos Humanos: vacaciones, licencias, nomina, beneficios, desempeno, conducta."""

from langchain_core.language_models import BaseChatModel

from src.agents.rag_agent import RAGAgent
from src.vector_store import get_retriever

DOMAIN = "hr"
AREA = "Recursos Humanos"
SCOPE_NOTE = (
    "Tu área es Recursos Humanos (vacaciones, licencias, sueldos y recibos, beneficios, desempeño, "
    "trabajo híbrido, conducta). Si la pregunta incluye una parte técnica (por ejemplo, no poder "
    "entrar a un portal) o de gastos y reembolsos, respondé lo que figure en tus fragmentos y aclará "
    "que esa otra parte la resuelve Soporte Técnico o Finanzas."
)


def build_hr_agent(llm: BaseChatModel | None = None, **retriever_kwargs) -> RAGAgent:
    return RAGAgent(
        DOMAIN, AREA, SCOPE_NOTE, get_retriever(DOMAIN, **retriever_kwargs), llm
    )
