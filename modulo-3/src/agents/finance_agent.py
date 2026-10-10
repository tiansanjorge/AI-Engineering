"""Agente de Finanzas: gastos y reembolsos, facturacion a clientes, compras, presupuesto, impuestos."""

from langchain_core.language_models import BaseChatModel

from src.agents.rag_agent import RAGAgent
from src.vector_store import get_retriever

DOMAIN = "finance"
AREA = "Finanzas"
SCOPE_NOTE = (
    "Tu área es Finanzas (gastos y reembolsos, viáticos, facturación y cobranzas a clientes, planes y "
    "tarifas, compras y proveedores, presupuesto, impuestos). No respondés sobre sueldos, vacaciones ni "
    "beneficios (Recursos Humanos), ni sobre fallas técnicas (Soporte Técnico), ni das asesoramiento legal. "
    "Vocabulario: quien te consulta es una persona empleada. «Reembolso» sin más aclaración se refiere al "
    "reembolso de gastos de la persona empleada (viajes, comidas, formación), que se pide cargando un informe "
    "de gastos en Nimbus Expenses: «pedir un reembolso» equivale a «presentar un informe de gastos» y su plazo "
    "es el plazo para presentarlo. Los reembolsos a clientes (de un cargo por su plan) son otro tema y solo "
    "los usás si la consulta habla de clientes."
)


def build_finance_agent(
    llm: BaseChatModel | None = None, **retriever_kwargs
) -> RAGAgent:
    return RAGAgent(
        DOMAIN, AREA, SCOPE_NOTE, get_retriever(DOMAIN, **retriever_kwargs), llm
    )
