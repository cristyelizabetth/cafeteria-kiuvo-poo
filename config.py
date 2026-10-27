"""Configuración de la aplicación.

Los datos delicados (clave secreta, modo debug) se leen de variables de
entorno, no se escriben en el código que se sube a GitHub.
"""

import os
import secrets
from datetime import timedelta
from pathlib import Path

CARPETA_BASE = Path(__file__).resolve().parent
CARPETA_INSTANCIA = CARPETA_BASE / "instancia"   # está en .gitignore: no se sube a GitHub


def obtener_clave_secreta():
    """Usa KIUVO_SECRET_KEY si existe; si no, genera una y la guarda en instancia/.

    La clave secreta firma la cookie de sesión. Si alguien la conoce, podría
    fabricar una sesión de administrador; por eso nunca va en el código.
    """
    clave = os.environ.get("KIUVO_SECRET_KEY")
    if clave:
        return clave
    CARPETA_INSTANCIA.mkdir(exist_ok=True)
    archivo = CARPETA_INSTANCIA / "clave_secreta.txt"
    if archivo.exists():
        return archivo.read_text().strip()
    clave = secrets.token_hex(32)
    archivo.write_text(clave)
    return clave


class Configuracion:
    SECRET_KEY = obtener_clave_secreta()
    BASE_DATOS = os.environ.get("KIUVO_BASE_DATOS", str(CARPETA_INSTANCIA / "kiuvo.db"))

    # Debug apagado salvo que se pida explícitamente (KIUVO_DEBUG=1).
    DEBUG = os.environ.get("KIUVO_DEBUG") == "1"

    # Cookie de sesión segura
    SESSION_COOKIE_HTTPONLY = True        # JavaScript no puede leerla
    SESSION_COOKIE_SAMESITE = "Lax"       # no se envía en formularios de otros sitios
    SESSION_COOKIE_SECURE = os.environ.get("KIUVO_COOKIE_SEGURA") == "1"  # solo HTTPS (activar al publicar)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    MAX_CONTENT_LENGTH = 1024 * 1024      # rechaza formularios de más de 1 MB

    INTENTOS_LOGIN = 5
    SEGUNDOS_BLOQUEO = 5 * 60
