"""Permite `from src.agents.orchestrator import ...` desde los tests y el
notebook, igual que si estuvieramos parados en la raiz de modulo-3/."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
