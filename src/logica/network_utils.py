"""Utilidades de red consolidadas."""

from socket import socket, AF_INET, SOCK_DGRAM
from ipaddress import ip_network


def get_local_ip():
    """Obtiene IP local del equipo."""
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def get_local_network(cidr="/16"):
    """Obtiene red local con CIDR especificado.

    Args:
        cidr: Sufijo CIDR (ej: "/16", "/24")

    Returns:
        ipaddress.IPv4Network: Red local
    """
    ip = get_local_ip()
    return ip_network(ip + cidr, strict=False)
