"""Modelos Pydantic: el contrato de datos del sistema.

Idea central: el LLM es una fuente NO confiable de datos. Pydantic es la frontera que separa "lo
que dijo el modelo" de "lo que el resto del sistema acepta". Si algo no cumple el contrato,
falla ahi, con un error claro, y no se propaga como dato basura a otros sistemas.

Hay dos modelos a proposito:
  - `ExtractionResult` (interno): lo que produce el agente extractor, con el detalle de cada
    cambio y su tipo (adicion / eliminacion / modificacion).
  - `ContractChangeOutput` (publico): el contrato EXACTO de la consigna, con 3 campos. Se DERIVA
    del anterior por codigo, no se le pide al LLM, asi `sections_changed` y `topics_touched`
    nunca pueden contradecir al detalle de los cambios.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_unique(values: list[str], field: str) -> list[str]:
    """Quita espacios, rechaza items vacios y elimina duplicados conservando el orden."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(value.split())  # colapsa espacios y saltos de linea
        if not text:
            raise ValueError(f"'{field}' no puede contener elementos vacios")
        if text.casefold() not in seen:
            seen.add(text.casefold())
            cleaned.append(text)
    return cleaned


def _meaningful_summary(value: str) -> str:
    text = " ".join(value.split())
    # Piso bajo: descarta "ok", "sin cambios" o cadenas vacias; no pretende medir calidad.
    if len(text) < 20:
        raise ValueError("el resumen es demasiado corto para describir los cambios")
    return text


class ChangeType(StrEnum):
    """Los tres tipos de cambio que distingue la consigna. Un enum cerrado impide que el modelo
    invente categorias como 'actualizacion' o 'ajuste'."""

    ADDITION = "adicion"
    DELETION = "eliminacion"
    MODIFICATION = "modificacion"


class ExtractedChange(BaseModel):
    """Un cambio individual introducido por la adenda."""

    section: str = Field(
        description="Identificador de la seccion afectada, p. ej. 'Cláusula Tercera' o "
        "'Cláusula Cuarta, inciso 4.3'."
    )
    change_type: ChangeType = Field(
        description="adicion (texto nuevo), eliminacion (texto que se quita) o modificacion "
        "(texto que cambia de valor o redaccion)."
    )
    topic: str = Field(
        description="Categoria legal o comercial afectada, p. ej. 'Precio', 'Plazo y vigencia'."
    )
    description: str = Field(
        description="Que cambio exactamente, con los valores antes y despues cuando existan."
    )

    @field_validator("section", "topic", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        text = " ".join(value.split())
        if not text:
            raise ValueError("el campo no puede estar vacio")
        return text


class ExtractionResult(BaseModel):
    """Salida del agente extractor: el detalle de los cambios y un resumen.

    Las restricciones (no vacio, largo minimo) se validan en Python y no con
    `Field(min_length=...)`: asi el esquema que ve el LLM queda simple y compatible con el modo
    estricto de structured outputs, y la validacion igual se aplica siempre.
    """

    changes: list[ExtractedChange] = Field(
        description="Un elemento por cada cambio aislado que introduce la adenda."
    )
    summary_of_the_change: str = Field(
        description="Descripcion detallada y fiel de los cambios, en prosa, para un abogado."
    )

    @field_validator("changes")
    @classmethod
    def at_least_one_change(cls, value: list[ExtractedChange]) -> list[ExtractedChange]:
        # Una adenda por definicion modifica algo: "cero cambios" casi seguro es un error
        # (parsing fallido o modelo perdido) y debe salir como error, no como resultado vacio.
        if not value:
            raise ValueError("se esperaba al menos un cambio, pero la lista esta vacia")
        return value

    @field_validator("summary_of_the_change")
    @classmethod
    def meaningful_summary(cls, value: str) -> str:
        return _meaningful_summary(value)

    def to_output(self) -> "ContractChangeOutput":
        """Deriva el contrato publico: secciones y temas salen del detalle, sin ir al LLM."""
        return ContractChangeOutput(
            sections_changed=[c.section for c in self.changes],
            topics_touched=[c.topic for c in self.changes],
            summary_of_the_change=self.summary_of_the_change,
        )


class ContractChangeOutput(BaseModel):
    """Contrato de salida del sistema (los 3 campos que exige la consigna)."""

    # extra="forbid": cualquier campo no declarado es un error, no se ignora en silencio.
    model_config = ConfigDict(extra="forbid")

    sections_changed: list[str] = Field(
        description="Identificadores de las secciones modificadas, sin duplicados."
    )
    topics_touched: list[str] = Field(
        description="Categorias legales/comerciales afectadas, sin duplicados."
    )
    summary_of_the_change: str = Field(
        description="Descripcion detallada de los cambios introducidos por la adenda."
    )

    @field_validator("sections_changed", "topics_touched")
    @classmethod
    def clean_non_empty_list(cls, value: list[str], info) -> list[str]:
        cleaned = _clean_unique(value, info.field_name)
        if not cleaned:
            raise ValueError(f"'{info.field_name}' no puede estar vacia")
        return cleaned

    @field_validator("summary_of_the_change")
    @classmethod
    def meaningful_summary(cls, value: str) -> str:
        return _meaningful_summary(value)
