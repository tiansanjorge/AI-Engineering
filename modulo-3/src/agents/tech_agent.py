"""Agente de Soporte Tecnico (IT): accesos, VPN y red, equipos y software, incidentes, seguridad."""

from langchain_core.language_models import BaseChatModel

from src.agents.rag_agent import RAGAgent
from src.vector_store import get_retriever

DOMAIN = "tech"
AREA = "Soporte Técnico"
SCOPE_NOTE = (
    "Tu área es Soporte Técnico (cuentas y contraseñas, MFA, VPN y red, notebooks y software, "
    "mesa de ayuda e incidentes, seguridad). Resolvés problemas técnicos, incluso de acceso a "
    "portales como Nimbus People o Nimbus Expenses, pero no el contenido de esos portales: las "
    "políticas de personal corresponden a Recursos Humanos y los reembolsos, compras y facturas a Finanzas."
)


def build_tech_agent(llm: BaseChatModel | None = None, **retriever_kwargs) -> RAGAgent:
    return RAGAgent(
        DOMAIN, AREA, SCOPE_NOTE, get_retriever(DOMAIN, **retriever_kwargs), llm
    )
