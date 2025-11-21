import ipaddress
from re import compile

reg_ex = compile(
    r"^(10)(\.1[0-1][0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[1-9]|0)){2}$"
)
romper = False


def calculate_ip_range(ip_start="10.100.0.0", ip_end=None):
    """
    Calcula el rango de IPs entre dos direcciones IP dadas.
    Si la mascara es mayor a /16 advertir que puede tardar (hacer calculo de tiempo estimado realista)
    Args:
        ip_start (str): Dirección IP de inicio en formato decimal con puntos.
        ip_end (str): Dirección IP de fin en formato decimal con puntos.
    Returns:
        tuple: (subred1, subred2) donde cada subred es un objeto ipaddress.IPv4Network.
    Raises:
        ValueError: Si las direcciones IP no son válidas.
    """
    global romper
    if not ip_end:
        ip_end = ip_start
    try:
        a = reg_ex.match(ip_start)
        if not a:
            romper = True
            print("IP de inicio no válida")
            return
    except Exception:
        romper = True
        print("Error al validar IP de inicio")
        return

    def ip_to_binary_string(ip):
        """
        Convierte una IP en cadena binaria dividida en octetos.
        Args:
            ip (str): Dirección IP en formato decimal con puntos.
        Returns:
            tuple: (primer_octeto, segundo_octeto, tercer_octeto, cuarto_octeto
        """
        ip_int = int(ipaddress.ip_address(ip))  # Convierte IP a entero
        binary_str = bin(ip_int)[2:].zfill(32)  # Quita '0b' y rellena a 32 bits
        return binary_str

    #   conversor a subredes
    def calculate_network_mask(ip_bin_start, ip_bin_end):
        ip_bin = int(ip_bin_end, 2) - int(ip_bin_start, 2)
        print(ip_bin, "ip binaria restada")

        def obtener_mascara(ip_bin):
            potencia = 0
            resultado = 1
            while 2 ** potencia < ip_bin:
                resultado *= 2
                potencia += 1
            return potencia

        potencia = obtener_mascara(ip_bin)
        mascara = 32 - potencia
        print("Máscara calculada:", mascara)

        def Calcular_IP_base(ip_bin_start, mascara):
            ip_start_int = int(ip_bin_start, 2)
            block_size = 2 ** (32 - mascara)
            base_int = (ip_start_int // block_size) * block_size
            base_ip = ipaddress.ip_address(base_int)
            subnet1 = ipaddress.ip_network(f"{base_ip}/{mascara}", strict=False)
            return subnet1

        ip_mask1 = Calcular_IP_base(ip_bin_start, mascara)
        diferencia = int(ip_bin_end,2) - int(ip_to_binary_string(ip_mask1.compressed[:-3]),2)
        
        restante =  diferencia - ip_mask1.num_addresses
        print("Diferencia con potencia encontrada:", restante)
        if restante > 0:
            potencia = obtener_mascara(restante)
            mascara = 32 - potencia
        ip_mask2 = Calcular_IP_base(
            ip_to_binary_string(ip_mask1.broadcast_address + 1), mascara
        )
        return ip_mask1, ip_mask2 if ip_mask2 else None

    return calculate_network_mask(
        ip_to_binary_string(ip_start), ip_to_binary_string(ip_end)
    )


if __name__ == "__main__":
    try:
        ip_inicio = "10.100.1.100"
        ip_fin = "10.100.1.120"
        print("IP inicio:", ip_inicio)
        print("IP fin:", ip_fin)
        remaining_last_octet = calculate_ip_range(ip_inicio, ip_fin)
        print(remaining_last_octet, "IPs en el rango")
    except Exception:
        print("Error inesperado:", Exception)
