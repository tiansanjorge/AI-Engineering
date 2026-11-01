"""Configuracion de pytest: pone modulo-4/ en sys.path y apaga el tracing real de Langfuse.

Los tests NUNCA deben mandar trazas a la nube ni depender de la red: con el tracing desactivado
el SDK devuelve spans "vacios" y el codigo se ejecuta igual (justo lo que hay que verificar).
"""

import os

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
