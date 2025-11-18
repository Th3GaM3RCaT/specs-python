from re import compile
reg_ex = compile(r'^(10)(\.1[0-1][0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]|[1-9]|0)){2}$')
romper = False
def calculate_ip_range(ip_start = "10.100.0.0", ip_end = None):
    global romper
    if not ip_end: ip_end = ip_start
    try:
        a = reg_ex.match(ip_start)
        if not a:romper = True
    except Exception:romper = True
    
    def last_oct(ip):    
        sIp = ip[-3:]
        if sIp[-3] == ".":      sIp = sIp[-2:]
        elif sIp[-2] == ".":    sIp = sIp[-1:]
        return int(sIp)
    
    last_oct_start = last_oct(ip_start)
    last_oct_end = last_oct(ip_end)
    last_oct_end-=last_oct_start
    if not romper:return last_oct_end
    else: return None

#hacer potencias de 2 hasta alcanzar el valor de extract_last_octet
def potencia_de_2_hasta(valor):
    print()
    print ("="*20, "Cálculo de potencia de 2 para valor:", valor)
    potencia = 0
    resultado = 1
    while resultado < valor:
        resultado *= 2
        potencia += 1
    diferencia = valor - resultado
    print("Potencia encontrada:", potencia)
    potencia -=1
    print("Potencia ajustada:", potencia)
    print ("host:",2**potencia)
    print("Diferencia:", diferencia)
    
    potencia = 32-potencia
    print ("Máscara de subred sugerida:", potencia)
    print ("="*20)
    return potencia





if __name__ == "__main__":
    while True:
        try:
            print("IP inicio: 10.100.2.10")
            print("IP fin: 10.100.2.150")
            remaining_last_octet = calculate_ip_range("10.100.2.10", "10.100.2.150")
            print("restante del último octeto:", remaining_last_octet)
            print(potencia_de_2_hasta(remaining_last_octet))
            # todo: crear lista de subredes para rellenar cantidad restante
            
            input("Presione Enter para continuar...")
            if romper: break
        except Exception as e:
            print("Error:", e)
            break