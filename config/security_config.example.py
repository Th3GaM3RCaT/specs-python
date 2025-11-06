# TEMPLATE de configuración de seguridad
# Copiar este archivo como security_config.py y configurar valores

import hmac
import hashlib
import time
from ipaddress import ip_address, ip_network

# ============================================================================
# CONFIGURAR ESTOS VALORES ANTES DE USAR
# ============================================================================

# Token secreto compartido (cliente y servidor deben tener el mismo)
# GENERAR con: python -c "import secrets; print(secrets.token_hex(32))"
SHARED_SECRET = "CHANGE_ME_TO_RANDOM_TOKEN_64_CHARS_MINIMUM_____________________"

# Subnets permitidas (CIDR notation)
# Agregar todas las subredes de tu organización
ALLOWED_SUBNETS = [
    "10.100.0.0/16",  # Ejemplo: Red corporativa sede principal
    "10.119.0.0/16",  # Ejemplo: Red corporativa sede remota
    "127.0.0.1/32",   # localhost
    "192.168.0.0/16", # Redes privadas comunes
]

# Límites de seguridad
MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 10 MB - tamaño máximo de datos recibidos
CONNECTION_TIMEOUT = 30              # 30 segundos - timeout de conexión TCP
MAX_CONNECTIONS_PER_IP = 3           # Máximo 3 conexiones por IP
MAX_FIELD_LENGTH = 1024              # 1024 caracteres - longitud máxima de campos de texto

# ============================================================================
# NO MODIFICAR EL CÓDIGO DEBAJO DE ESTA LÍNEA
# ============================================================================

def generate_auth_token():
    """
    Genera token de autenticación HMAC-SHA256 basado en timestamp.
    Token válido por 5 minutos (300 segundos).
    """
    if SHARED_SECRET == "CHANGE_ME_TO_RANDOM_TOKEN_64_CHARS_MINIMUM_____________________":
        raise ValueError(
            "SHARED_SECRET no configurado. "
            "Generar con: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    
    # Window de 5 minutos (300 segundos)
    timestamp = str(int(time.time() // 300))
    message = f"specs_auth_{timestamp}"
    
    token = hmac.new(
        SHARED_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return token


def verify_auth_token(token):
    """
    Verifica token de autenticación.
    Acepta token de ventana actual y ventana anterior (5 minutos cada una).
    """
    if not token:
        return False
    
    # Verificar ventana actual y anterior para tolerar clock skew
    current_window = str(int(time.time() // 300))
    previous_window = str(int(time.time() // 300) - 1)
    
    for window in [current_window, previous_window]:
        message = f"specs_auth_{window}"
        expected_token = hmac.new(
            SHARED_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Usar compare_digest para prevenir timing attacks
        if hmac.compare_digest(token, expected_token):
            return True
    
    return False


def is_ip_allowed(ip_str):
    """
    Verifica si una IP está en las subnets permitidas.
    """
    try:
        ip = ip_address(ip_str)
        
        for subnet_str in ALLOWED_SUBNETS:
            subnet = ip_network(subnet_str)
            if ip in subnet:
                return True
        
        return False
    except Exception:
        return False


def sanitize_field(value, max_length=MAX_FIELD_LENGTH):
    """
    Sanitiza campos de texto:
    - Trunca a max_length caracteres
    - Remueve caracteres de control (excepto \\n, \\r, \\t)
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Truncar longitud
    value = value[:max_length]
    
    # Remover caracteres de control (ord < 32) excepto newline, return, tab
    value = ''.join(
        char for char in value 
        if ord(char) >= 32 or char in '\n\r\t'
    )
    
    return value


# ============================================================================
# TESTING - Descomentar para probar configuración
# ============================================================================

if __name__ == "__main__":
    print("🔐 Testing security_config.py\n")
    
    # Test 1: Token generation
    try:
        token = generate_auth_token()
        print(f"✅ Token generado: {token[:16]}...")
    except Exception as e:
        print(f"❌ Error generando token: {e}")
    
    # Test 2: Token verification
    try:
        is_valid = verify_auth_token(token) # type: ignore
        print(f"✅ Token válido: {is_valid}")
    except Exception as e:
        print(f"❌ Error verificando token: {e}")
    
    # Test 3: IP validation
    test_ips = ["10.100.1.1", "192.168.1.1", "8.8.8.8", "127.0.0.1"]
    for ip in test_ips:
        allowed = is_ip_allowed(ip)
        status = "✅ Permitida" if allowed else "❌ Bloqueada"
        print(f"{status}: {ip}")
    
    # Test 4: Field sanitization
    test_field = "A" * 2000 + "\x00\x01\x02"
    sanitized = sanitize_field(test_field)
    print(f"✅ Sanitización: {len(test_field)} chars → {len(sanitized)} chars")
    
    print("\n✅ Configuración de seguridad validada")
