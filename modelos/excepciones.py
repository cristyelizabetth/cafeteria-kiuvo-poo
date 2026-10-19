"""Excepciones propias de la cafetería.

Todas heredan de ErrorCafeteria, así las rutas pueden atrapar cualquier
error del negocio con un solo `except ErrorCafeteria` y mostrar su mensaje.
"""


class ErrorCafeteria(Exception):
    """Clase base de todos los errores del negocio."""


class DatosInvalidos(ErrorCafeteria):
    """Algún dato de un formulario no es válido."""


class InventarioInsuficiente(ErrorCafeteria):
    """Se pidió más cantidad de la que hay en existencia."""

    def __init__(self, nombre_producto, disponibles):
        self.nombre_producto = nombre_producto
        self.disponibles = disponibles
        super().__init__(
            f"No hay suficiente inventario de «{nombre_producto}». "
            f"Disponibles: {disponibles}."
        )


class ProductoNoDisponible(ErrorCafeteria):
    """El producto está desactivado o agotado."""


class PedidoNoCancelable(ErrorCafeteria):
    """El pedido ya no se puede cancelar."""


class CredencialesInvalidas(ErrorCafeteria):
    """Correo, contraseña o respuesta de seguridad incorrectos."""


class CuentaBloqueada(ErrorCafeteria):
    """Demasiados intentos fallidos seguidos."""

    def __init__(self, segundos_restantes):
        self.segundos_restantes = segundos_restantes
        minutos = max(1, round(segundos_restantes / 60))
        super().__init__(
            f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s)."
        )


class ContrasenaInvalida(ErrorCafeteria):
    """La contraseña no cumple las reglas de seguridad."""


class CorreoYaRegistrado(ErrorCafeteria):
    """Ya existe una cuenta con ese correo."""
