"""Prueba de humo del entorno del Modulo 3.

Verifica, con llamadas reales y de costo despreciable:
  1. Langfuse: credenciales y region validas.
  2. Chroma: coleccion persistente + filtro por metadatos.
  3. LangGraph: ruteo condicional minimo.
  4. LangChain + Langfuse: una llamada al LLM queda trazada y se puede leer de vuelta.

Uso (desde modulo-3/):  python scripts/smoke_test.py
"""

import os
import tempfile
import time
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()


def check_langfuse() -> None:
    from langfuse import get_client

    ok = get_client().auth_check()
    assert ok, (
        "Langfuse rechazo las credenciales (revisar claves y LANGFUSE_HOST/region)"
    )
    print(
        f"[ok] Langfuse auth ({os.getenv('LANGFUSE_HOST') or os.getenv('LANGFUSE_BASE_URL')})"
    )


def check_chroma() -> None:
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    with tempfile.TemporaryDirectory() as tmp:
        store = Chroma(
            collection_name="smoke",
            embedding_function=embeddings,
            persist_directory=tmp,
        )
        store.add_documents(
            [
                Document(
                    page_content="Cómo pedir vacaciones", metadata={"domain": "hr"}
                ),
                Document(
                    page_content="Cómo resetear la VPN", metadata={"domain": "tech"}
                ),
            ]
        )
        hits = store.similarity_search("vacaciones", k=2, filter={"domain": "tech"})
        assert [h.metadata["domain"] for h in hits] == ["tech"], hits
        store._client.close() if hasattr(store._client, "close") else None
    print("[ok] Chroma persistente + filtro por metadatos")


def check_langgraph() -> None:
    from langgraph.graph import END, START, StateGraph

    class S(TypedDict, total=False):
        q: str
        route: str

    g = StateGraph(S)
    g.add_node(
        "router", lambda s: {"route": "hr" if "vacaciones" in s["q"] else "tech"}
    )
    g.add_node("hr", lambda s: {"q": "hr-ok"})
    g.add_node("tech", lambda s: {"q": "tech-ok"})
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: s["route"], ["hr", "tech"])
    g.add_edge("hr", END)
    g.add_edge("tech", END)
    assert g.compile().invoke({"q": "vacaciones"})["q"] == "hr-ok"
    print("[ok] LangGraph routing condicional")


def check_traced_llm_call() -> None:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler

    handler = CallbackHandler()
    chain = ChatPromptTemplate.from_template(
        "Responde solo 'pong'. Mensaje: {m}"
    ) | ChatOpenAI(model=os.getenv("CHAT_MODEL", "gpt-4o-mini"), temperature=0)
    out = chain.invoke({"m": "ping"}, config={"callbacks": [handler]})
    client = get_client()
    client.flush()
    trace_id = handler.last_trace_id
    assert trace_id, "El handler no devolvio trace_id"
    print(f"[ok] LLM respondio {out.content!r}; trace_id={trace_id}")
    # La API legacy de traces (GET /traces/{id}) devuelve 410 en organizaciones nuevas:
    # se lee con la API de observaciones v2, que puede tardar unos segundos en reflejar el trace.
    for _ in range(10):
        obs = client.api.observations.get_many(trace_id=trace_id, limit=20).data
        if obs:
            print(
                f"[ok] Trace leido de vuelta (observaciones: {sorted({o.name for o in obs})})"
            )
            return
        time.sleep(3)
    raise AssertionError("El trace no aparecio en Langfuse tras 30s")


if __name__ == "__main__":
    for step in (check_langfuse, check_chroma, check_langgraph, check_traced_llm_call):
        step()
    print("Smoke test completo.")
