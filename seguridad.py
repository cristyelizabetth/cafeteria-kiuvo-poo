"""Clases de seguridad: reglas de contraseña, límite de intentos y token CSRF."""

import re
import secrets
import time

from modelos.excepciones import ContrasenaInvalida


class ValidadorContrasena:
    """Revisa que una contraseña cumpla las reglas mínimas."""

    LONGITUD_MINIMA = 8

    @classmethod
    def errores(cls, contrasena):
        """Devuelve la lista de reglas que la contraseña NO cumple."""
        errores = []
        if len(contrasena) < cls.LONGITUD_MINIMA:
            errores.append(f"Debe tener al menos {cls.LONGITUD_MINIMA} caracteres.")
        if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", contrasena):
            errores.append("Debe incluir al menos una letra.")
        if not re.search(r"\d", contrasena):
            errores.append("Debe incluir al menos un número.")
        if contrasena != contrasena.strip():
            errores.append("No debe empezar ni terminar con espacios.")
        return errores

    @classmethod
    def validar(cls, contrasena):
        """Lanza ContrasenaInvalida si la contraseña no cumple las reglas."""
        errores = cls.errores(contrasena)
        if errores:
            raise ContrasenaInvalida(" ".join(errores))


class LimitadorIntentos:
    """Bloquea temporalmente una cuenta después de varios intentos fallidos.

    Se guarda en memoria: si el servidor se reinicia, los contadores vuelven a cero.
    """

    def __init__(self, maximo_intentos=5, segundos_bloqueo=300, reloj=time.monotonic):
        self._maximo = maximo_intentos
        self._segundos_bloqueo = segundos_bloqueo
        self._reloj = reloj          # se puede cambiar en las pruebas
        self._fallos = {}            # clave -> cantidad de fallos seguidos
        self._bloqueados = {}        # clave -> momento en que termina el bloqueo

    def segundos_restantes(self, clave):
        """0 si la clave no está bloqueada; si lo está, cuántos segundos faltan."""
        fin = self._bloqueados.get(clave)
        if fin is None:
            return 0
        restantes = fin - self._reloj()
        if restantes <= 0:
            self.reiniciar(clave)
            return 0
        return restantes

    def registrar_fallo(self, clave):
        self._fallos[clave] = self._fallos.get(clave, 0) + 1
        if self._fallos[clave] >= self._maximo:
            self._bloqueados[clave] = self._reloj() + self._segundos_bloqueo
            self._fallos[clave] = 0

    def intentos_restantes(self, clave):
        return self._maximo - self._fallos.get(clave, 0)

    def reiniciar(self, clave):
        self._fallos.pop(clave, None)
        self._bloqueados.pop(clave, None)


class ProtectorCSRF:
    """Protege los formularios contra CSRF (peticiones falsificadas desde otro sitio).

    Cada sesión recibe un token secreto. Todos los formularios lo envían en un
    campo oculto y el servidor rechaza los POST que no lo traen o traen otro.
    """

    CLAVE_SESION = "_csrf_token"
    NOMBRE_CAMPO = "csrf_token"

    def token(self, sesion):
        if self.CLAVE_SESION not in sesion:
            sesion[self.CLAVE_SESION] = secrets.token_hex(32)
        return sesion[self.CLAVE_SESION]

    def es_valido(self, sesion, token_recibido):
        esperado = sesion.get(self.CLAVE_SESION)
        if not esperado or not token_recibido:
            return False
        return secrets.compare_digest(esperado, token_recibido)
