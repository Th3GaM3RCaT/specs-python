import subprocess

def get_from_inform(objeto="Card name:",is_in = False):
    try:
        if not is_in:
            output = subprocess.check_output(
                ["dxdiag", "/t", "dxdiag_output.txt"],
                text=True
            )
        with open("dxdiag_output.txt", "r", encoding="cp1252") as f:
            lines = f.readlines()
        gpus = []
        for line in lines:
            if objeto in line:
                gpus.append(line.split(":",1)[1].strip())
        return gpus
    except Exception:
        return []
if __name__ == "__main__":
    print(get_from_inform())
