import subprocess

def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True)
        return out.strip()
    except Exception:
        return ""

def get_serial():
    # try WMI python module first
    try:
        import wmi
        c = wmi.WMI()
        bios = c.Win32_BIOS()
        if bios:
            s = bios[0].SerialNumber
            if s:
                return s.strip()
    except Exception:
        pass
    # fallback: powershell Get-CimInstance
    ps = ["powershell", "-NoProfile", "-Command",
          "Get-CimInstance -ClassName Win32_BIOS | Select-Object -ExpandProperty SerialNumber"]
    out = run_cmd(ps)
    if out:
        return out
    # older systems: wmic (deprecated on some Windows)
    out = run_cmd(["wmic", "bios", "get", "serialnumber"])
    if out:
        lines = [l.strip() for l in out.splitlines() if l.strip() and "SerialNumber" not in l]
        if lines:
            return lines[0]
    return ""

if __name__ == "__main__":
    s = get_serial()
    if s:
        print("Serial encontrado:", s)
    else:
        print("No se pudo encontrar un serial desde el sistema.")
