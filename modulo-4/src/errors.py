"""Excepciones propias del pipeline.

Cada tipo de falla tiene su clase: asi `main.py` puede explicar QUE paso fallo y POR QUE con un
mensaje claro, en vez de mostrar un traceback generico. Todas heredan de `ContractAnalysisError`,
por lo que un solo `except` captura cualquier falla controlada del sistema.
"""


class ContractAnalysisError(Exception):
    """Base de todas las fallas controladas del pipeline."""


class ConfigError(ContractAnalysisError):
    """Falta configuracion obligatoria (p. ej. OPENAI_API_KEY). Se detecta antes de empezar."""


class InvalidImageError(ContractAnalysisError):
    """La imagen de entrada no sirve: no existe, formato no soportado, vacia o muy pesada.

    Se detecta ANTES de llamar a la API: no tiene sentido gastar tokens con un archivo roto.
    """


class ModelAPIError(ContractAnalysisError):
    """La llamada a un modelo (vision o agente) fallo tras agotar los reintentos."""


class EmptyParseError(ContractAnalysisError):
    """El modelo respondio, pero sin texto util (p. ej. la imagen no era un documento legible)."""


class OutputValidationError(ContractAnalysisError):
    """La salida final del agente no cumple el contrato Pydantic, ni siquiera tras reintentar.

    Guarda el detalle del error y la salida cruda para poder auditar que devolvio el modelo.
    """

    def __init__(self, message: str, *, raw_output: object = None):
        super().__init__(message)
        self.raw_output = raw_output
