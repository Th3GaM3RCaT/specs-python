import wmi

def get_ram_info():
    c = wmi.WMI()
    ram_modules = []
    for mem in c.Win32_PhysicalMemory():
        ram_modules.append({
            "Fabricante": mem.Manufacturer,
            "Etiqueta": mem.Tag,
            "Número_de_Serie": mem.SerialNumber.strip() if mem.SerialNumber else None,
            "Capacidad_GB": round(int(mem.Capacity) / (1024**3), 2),
            "Velocidad_MHz": mem.Speed,
            "Tipo": mem.MemoryType,
            "Factor_de_Forma": mem.FormFactor,
            "Banco": mem.BankLabel,
            "Parte": mem.PartNumber.strip() if mem.PartNumber else None
        })
    return ram_modules

if __name__ == "__main__":
    rams = get_ram_info()
    
    for i, ram in enumerate(rams, 1):
        print(f"--- Módulo RAM {i} ---")
        for k, v in ram.items():
            print(f"{k}: {v}")
        print()
