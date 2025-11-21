import subprocess
from pathlib import Path

# Directorio para archivos de salida
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
DXDIAG_OUTPUT = OUTPUT_DIR / "dxdiag_output.txt"


def get_from_inform(objeto="Card name:"):
    """
    Extrae información del reporte DirectX.

    Args:
        objeto: Texto a buscar en el reporte (ej: "Card name:", "Processor:")

    Returns:
        Lista de valores encontrados
    """
    try:
        # Generar reporte DirectX
        subprocess.check_output(["dxdiag", "/t", str(DXDIAG_OUTPUT)], text=True)

        # Leer y parsear
        with open(DXDIAG_OUTPUT, "r", encoding="cp1252") as f:
            lines = f.readlines()

        resultados = []
        for line in lines:
            if objeto in line:
                resultados.append(line.split(":", 1)[1].strip())

        return resultados
    except Exception:
        return []


if __name__ == "__main__":
    print(get_from_inform())
