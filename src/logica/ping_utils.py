"""Utilidades de ping asíncrono reutilizables para el proyecto.
Provee `ping_one_cmd` y `ping_host` con manejo cross-platform y sin ventanas en Windows.
"""

from asyncio import create_subprocess_exec, subprocess as asyncio_subprocess, wait_for
from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, SW_HIDE, CREATE_NO_WINDOW


async def ping_one_cmd(host: str, per_host_timeout: float) -> bool:
    """Ejecuta un ping a `host` devolviendo True si responde.

    per_host_timeout: segundos por ping (float)
    """
    try:

        # Windows: usar ping -n 1 -w <ms>
        cmd = ["ping", "-n", "1", "-w", str(int(per_host_timeout * 1000)), host]
        # Ocultar ventana en Windows
        startupinfo = STARTUPINFO()
        try:
            startupinfo.dwFlags |= STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = SW_HIDE
        except Exception:
            pass
        creationflags = 0
        try:
            creationflags = CREATE_NO_WINDOW
        except Exception:
            creationflags = 0
        proc = await create_subprocess_exec(
            *cmd,
            stdout=asyncio_subprocess.DEVNULL,
            stderr=asyncio_subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        ret = await proc.wait()
        return ret == 0
    except Exception:
        return False


async def ping_host(host: str, per_host_timeout: float) -> bool:
    """Wrapper que aplica timeout alrededor de ping_one_cmd.
    Devuelve False ante cualquier excepción o timeout.
    """
    try:
        return await wait_for(
            ping_one_cmd(host, per_host_timeout), timeout=per_host_timeout + 0.5
        )
    except Exception:
        return False
