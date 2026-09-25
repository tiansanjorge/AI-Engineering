"""Permite `import chunking`, `import query`, etc. desde los tests,
igual que si estuvieramos parados en src/."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
