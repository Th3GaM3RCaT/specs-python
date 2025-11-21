#!/usr/bin/env python3
"""
Wrapper para ejecutar el servidor desde la raíz del proyecto.
Ejecuta: python src/servidor.py
"""

import sys
from pathlib import Path

# Agregar src/ al path de Python
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Importar y ejecutar el módulo servidor
if __name__ == "__main__":
    # Cambiar directorio de trabajo a src/
    import os

    os.chdir(src_dir)

    # Importar servidor como módulo
    import mainServidor
