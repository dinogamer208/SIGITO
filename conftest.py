"""
conftest.py (raíz) — asegura que la raíz del proyecto esté en sys.path
al correr `pytest` desde cualquier carpeta, para que los tests puedan
hacer `from utils... import ...` igual que la app.
"""

import os
import sys

_RAIZ = os.path.dirname(os.path.abspath(__file__))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
