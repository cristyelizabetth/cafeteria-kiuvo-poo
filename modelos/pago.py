"""Métodos de pago simulados: MetodoPago (abstracta) → PagoEnCaja y PagoTarjetaSimulado.

Ninguno cobra dinero real: es una simulación para el proyecto.
"""

import secrets
from abc import ABC, abstractmethod


class MetodoPago(ABC):
    CLAVE = None

    @staticmethod
    def disponibles():
        return [PagoEnCaja(), PagoTarjetaSimulado()]

    @staticmethod
    def obtener(clave):
        for metodo in MetodoPago.disponibles():
            if metodo.CLAVE == clave:
                return metodo
        return None

    @abstractmethod
    def nombre(self):
        """Nombre que ve el estudiante."""

    @abstractmethod
    def descripcion(self):
        """Explicación corta en la página de pago."""

    @abstractmethod
    def procesar(self, total):
        """Simula el cobro y devuelve el mensaje de confirmación."""


class PagoEnCaja(MetodoPago):
    CLAVE = "caja"

    def nombre(self):
        return "Pagar en caja al retirar"

    def descripcion(self):
        return "Reservas ahora y pagas en la caja de la cafetería cuando recoges."

    def procesar(self, total):
        return f"Pedido confirmado. Paga ${total:.2f} en caja al retirar."


class PagoTarjetaSimulado(MetodoPago):
    CLAVE = "tarjeta"

    def nombre(self):
        return "Tarjeta (simulado)"

    def descripcion(self):
        return "Simula un pago con tarjeta. No se pide ni se cobra ninguna tarjeta real."

    def procesar(self, total):
        autorizacion = secrets.token_hex(3).upper()
        return (f"Pago simulado aprobado por ${total:.2f}. "
                f"Código de autorización: {autorizacion}.")
