"""Red de seguridad del ruteo basada en recuperacion.

Problema medido en la Fase 6: el router (LLM) a veces rechaza como `out_of_scope` consultas internas
legitimas (p. ej. "cuanto tiempo guardan el buzon de alguien que renuncio"). El prompt solo no lo
cierra del todo. Esta guarda agrega una segunda opinion independiente: si algun dominio tiene un
chunk MUY cercano a la consulta, un `out_of_scope` del router se considera un falso rechazo y la
consulta se rutea a ese dominio (el agente igual puede abstenerse si no hay respuesta).

El umbral `max_distance` (distancia coseno) se calibro con las distancias medidas en los sets dev y
de validacion: los falsos rechazos del router tenian distancia <= 0.377 y las consultas ajenas de
verdad >= 0.492 (excluyendo un caso adversarial con vocabulario de Finanzas, 0.386). Se tomo el punto
medio de esa brecha.
"""

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from src.config import DOMAINS
from src.vector_store import default_embeddings, get_store, nearest_distance

DEFAULT_MAX_DISTANCE = 0.43


class RetrievalGuard:
    def __init__(
        self,
        stores: dict[str, Chroma],
        embeddings: Embeddings,
        max_distance: float = DEFAULT_MAX_DISTANCE,
    ):
        self.stores = stores
        self.embeddings = embeddings
        self.max_distance = max_distance

    @classmethod
    def from_default(
        cls, max_distance: float = DEFAULT_MAX_DISTANCE
    ) -> "RetrievalGuard":
        embeddings = default_embeddings()
        stores = {d: get_store(d, embeddings=embeddings) for d in DOMAINS}
        return cls(stores, embeddings, max_distance)

    def closest_domain(self, question: str) -> tuple[str, float]:
        """Dominio cuya coleccion tiene el chunk mas cercano, y esa distancia."""
        vector = self.embeddings.embed_query(question)
        distances = {d: nearest_distance(s, vector) for d, s in self.stores.items()}
        domain = min(distances, key=distances.get)
        return domain, distances[domain]

    def veto(self, question: str) -> tuple[str, float] | None:
        """(dominio, distancia) si la recuperacion contradice un `out_of_scope`; si no, None."""
        domain, distance = self.closest_domain(question)
        return (domain, distance) if distance < self.max_distance else None
