# pytest lee este archivo automáticamente antes de correr los tests,
# sin que nadie lo importe explícitamente (es una convención de pytest,
# no de Python en general).
#
# Por qué hace falta: cuando corrés `python -m pytest` desde la raíz del
# proyecto, la carpeta raíz no está garantizado que esté en sys.path (la
# lista de carpetas donde Python busca módulos para importar). Sin esto,
# `from src.schema import validate_response` en tests/test_core.py
# fallaría con "no module named src". Estas dos líneas agregan la carpeta
# de este mismo archivo (la raíz del proyecto) a esa lista de búsqueda.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
