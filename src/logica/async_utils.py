"""Utilidades para manejo de funciones async desde código síncrono."""

import asyncio


def run_async(async_func, *args, **kwargs):
    """Ejecuta función async desde código síncrono.

    Args:
        async_func: Función asíncrona a ejecutar
        *args: Argumentos posicionales
        **kwargs: Argumentos nombrados

    Returns:
        Resultado de la función asíncrona
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        loop.close()
