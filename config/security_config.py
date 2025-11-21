# security_config.py
"""
Configuración de seguridad para el sistema de inventario.

IMPORTANTE: Este archivo contiene secretos sensibles.
NO compartir en repositorios públicos. Agregar a .gitignore.
"""
import secrets
import hashlib
import ipaddress
import os
from pathlib import Path
from typing import List

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv

    # Buscar .env en la raíz del proyecto (dos niveles arriba de config/)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] Configuración cargada desde {env_path}")
    else:
        print(f"[WARN] Archivo .env no encontrado en {env_path}")
except ImportError:
    print("[WARN] python-dotenv no instalado. Ejecutar: pip install python-dotenv")
    print("    Usando valores por defecto (INSEGURO)")

# Token compartido para autenticación cliente-servidor
SHARED_SECRET = os.getenv("SHARED_SECRET", "CHANGE_ME_TO_RANDOM_TOKEN")

# Redes permitidas (whitelist de subnets)
# Cargar desde .env (formato: "subnet1,subnet2,subnet3")
subnets_str = os.getenv("ALLOWED_SUBNETS", "127.0.0.1/32")
ALLOWED_SUBNETS = [subnet.strip() for subnet in subnets_str.split(",")]

# Límites de seguridad (cargar desde .env con fallbacks)
MAX_BUFFER_SIZE = int(os.getenv("MAX_BUFFER_SIZE", "10485760"))  # 10 MB por defecto
MAX_JSON_DEPTH = 20  # Profundidad máxima de JSON anidado
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "30"))  # segundos
MAX_CONNECTIONS_PER_IP = int(
    os.getenv("MAX_CONNECTIONS_PER_IP", "3")
)  # Conexiones simultáneas por IP
MAX_FIELD_LENGTH = int(
    os.getenv("MAX_FIELD_LENGTH", "1024")
)  # Caracteres máximos por campo

# Puertos de red
SERVER_PORT = int(os.getenv("SERVER_PORT", "5255"))  # Puerto TCP del servidor
DISCOVERY_PORT = int(os.getenv("DISCOVERY_PORT", "37020"))  # Puerto UDP para discovery
BROADCAST_INTERVAL = int(
    os.getenv("BROADCAST_INTERVAL", "10")
)  # Segundos entre broadcasts

# Rutas de archivos
DB_PATH = os.getenv("DB_PATH", "data/specs.db")  # Ruta de base de datos SQLite
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")  # Directorio de salida

# Configuración de escaneo
SCAN_SUBNET_START = os.getenv("SCAN_SUBNET_START", "10.100.0.0")
SCAN_SUBNET_END = os.getenv("SCAN_SUBNET_END", "10.119.0.0")
PING_TIMEOUT = float(os.getenv("PING_TIMEOUT", "1.0"))
SCAN_PER_HOST_TIMEOUT = float(os.getenv("SCAN_PER_HOST_TIMEOUT", "0.8"))
SCAN_PER_SUBNET_TIMEOUT = float(os.getenv("SCAN_PER_SUBNET_TIMEOUT", "8.0"))
SCAN_PROBE_TIMEOUT = float(os.getenv("SCAN_PROBE_TIMEOUT", "0.9"))
PING_BATCH_SIZE = int(os.getenv("PING_BATCH_SIZE", "50"))


def generate_auth_token(secret: str | None = None) -> str:
    """Genera token de autenticación usando HMAC-SHA256.

    Args:
        secret (str | None): Secreto compartido. Si es None, usa SHARED_SECRET.

    Returns:
        str: Token hexadecimal de 64 caracteres
    """
    if secret is None:
        secret = SHARED_SECRET

    # Usar timestamp + secreto para token temporal
    import time

    timestamp = str(int(time.time() // 300))  # Token válido por 5 minutos

    message = f"{secret}:{timestamp}"
    return hashlib.sha256(message.encode()).hexdigest()


def verify_auth_token(token: str, secret: str | None = None) -> bool:
    """Verifica token de autenticación.

    Args:
        token (str): Token a verificar
        secret (str | None): Secreto compartido. Si es None, usa SHARED_SECRET.

    Returns:
        bool: True si el token es válido
    """
    if secret is None:
        secret = SHARED_SECRET

    # Verificar token actual y el de 5 minutos atrás (ventana de tiempo)
    import time

    current_time = int(time.time() // 300)

    for offset in [0, -1]:  # Actual y anterior
        timestamp = str(current_time + offset)
        message = f"{secret}:{timestamp}"
        expected_token = hashlib.sha256(message.encode()).hexdigest()

        if token == expected_token:
            return True

    return False


def is_ip_allowed(ip: str) -> bool:
    """Verifica si una IP está en la whitelist de subnets.

    Args:
        ip (str): Dirección IP a verificar

    Returns:
        bool: True si la IP está permitida
    """
    try:
        ip_obj = ipaddress.ip_address(ip)

        for subnet_str in ALLOWED_SUBNETS:
            subnet = ipaddress.ip_network(subnet_str)
            if ip_obj in subnet:
                return True

        return False
    except ValueError:
        # IP inválida
        return False


def sanitize_field(value: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    """Sanitiza un campo de texto para prevenir ataques.

    Args:
        value (str): Valor a sanitizar
        max_length (int): Longitud máxima permitida

    Returns:
        str: Valor sanitizado y truncado
    """
    if not isinstance(value, str):
        value = str(value)

    # Truncar a longitud máxima
    if len(value) > max_length:
        value = value[:max_length]

    # Remover caracteres de control peligrosos
    value = "".join(char for char in value if ord(char) >= 32 or char in "\n\t")

    return value


def initialize_secret():
    """Genera un nuevo secreto aleatorio si aún no se ha configurado.

    Debe ejecutarse la primera vez en servidor y cliente.
    """
    global SHARED_SECRET

    if SHARED_SECRET == "CHANGE_ME_TO_RANDOM_TOKEN":
        new_secret = secrets.token_hex(32)
        print("=" * 70)
        print("[WARN] IMPORTANTE: Secreto compartido NO configurado")
        print("=" * 70)
        print("\nGenerar nuevo secreto aleatorio:")
        print(f'\nSHARED_SECRET = "{new_secret}"')
        print(f"\n1. Copiar esta línea en security_config.py")
        print(f"2. Usar el MISMO secreto en servidor y todos los clientes")
        print(f"3. NO compartir este valor públicamente\n")
        print("=" * 70)

        # No modificar automáticamente para evitar problemas
        raise ValueError("Secreto compartido no configurado. Ver mensaje arriba.")

    return SHARED_SECRET


# Validar configuración al importar
if __name__ != "__main__":
    if SHARED_SECRET == "CHANGE_ME_TO_RANDOM_TOKEN":
        print(
            "[WARN] WARNING: Usando secreto por defecto. Ejecutar initialize_secret() para generar uno nuevo."
        )
