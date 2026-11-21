"""Pedidos: un Pedido contiene varios ItemPedido (composición)."""

import re
import secrets
from datetime import datetime
from enum import Enum

from modelos.excepciones import CambioEstadoInvalido, DatosInvalidos, PedidoNoCancelable


class EstadoPedido(Enum):
    """Ciclo de vida de un pedido:

        PENDIENTE ──► ENTREGADO      (el estudiante lo retiró)
            │    └──► NO_RECOGIDO    (pagó o reservó, pero no llegó)
            └───────► CANCELADO      (el estudiante lo canceló; vuelve al inventario)
    """

    PENDIENTE = "pendiente"       # esperando ser retirado en la cafetería
    ENTREGADO = "entregado"
    NO_RECOGIDO = "no_recogido"
    CANCELADO = "cancelado"

    @property
    def texto(self):
        return {"pendiente": "Pendiente de retiro", "entregado": "Entregado",
                "no_recogido": "No recogido", "cancelado": "Cancelado"}[self.value]

    @property
    def es_final(self):
        """Un pedido entregado, no recogido o cancelado ya no cambia."""
        return self is not EstadoPedido.PENDIENTE


class ItemPedido:
    """Una línea del pedido.

    Guarda una copia del nombre y del precio en el momento de la compra:
    si después el admin cambia el precio, el pedido viejo no cambia.
    """

    def __init__(self, producto_id, nombre_producto, precio_unitario, cantidad):
        try:
            precio_unitario = round(float(precio_unitario), 2)
            cantidad_entera = int(cantidad)
        except (TypeError, ValueError):
            raise DatosInvalidos("El precio y la cantidad deben ser números.") from None
        if cantidad_entera != cantidad or cantidad_entera <= 0:
            raise DatosInvalidos("La cantidad debe ser un número entero mayor que 0.")
        if precio_unitario < 0:
            raise DatosInvalidos("El precio no puede ser negativo.")
        self.producto_id = producto_id
        self.nombre_producto = nombre_producto
        self.precio_unitario = precio_unitario
        self.cantidad = cantidad_entera

    @property
    def subtotal(self):
        return round(self.precio_unitario * self.cantidad, 2)


class Pedido:
    # Código de recibo: "KV-" + 6 letras o números, sin los que se confunden
    # al leerlos en voz alta (0/O, 1/I/L). Ejemplo: KV-7F3K9Q
    LETRAS_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    PATRON_CODIGO = re.compile(r"^KV-[A-HJ-NP-Z2-9]{6}$")

    def __init__(self, usuario_id, items, metodo_pago, estado=EstadoPedido.PENDIENTE,
                 fecha=None, id=None, nombre_cliente=None, codigo=None):
        if not items:
            raise DatosInvalidos("Un pedido debe tener al menos un producto.")
        self._id = id
        self.usuario_id = usuario_id
        self._items = list(items)
        self.metodo_pago = metodo_pago
        self._estado = estado
        self.fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.nombre_cliente = nombre_cliente
        self.codigo = codigo or self.generar_codigo()

    # ---------- Código de recibo ----------
    @classmethod
    def generar_codigo(cls):
        return "KV-" + "".join(secrets.choice(cls.LETRAS_CODIGO) for _ in range(6))

    @classmethod
    def normalizar_codigo(cls, texto):
        """'kv-7f3k9q', ' 7F3K9Q ' y 'KV-7F3K9Q' son el mismo código.

        Devuelve el código en su forma oficial, o lanza DatosInvalidos.
        """
        limpio = (texto or "").strip().upper().replace(" ", "")
        if not limpio:
            raise DatosInvalidos("Escribe el código del recibo.")
        if not limpio.startswith("KV-"):
            limpio = "KV-" + limpio.removeprefix("KV")
        if not cls.PATRON_CODIGO.match(limpio):
            raise DatosInvalidos("El código no es válido. Tiene la forma KV-7F3K9Q.")
        return limpio

    @property
    def codigo(self):
        return self._codigo

    @codigo.setter
    def codigo(self, valor):
        if not isinstance(valor, str) or not self.PATRON_CODIGO.match(valor):
            raise DatosInvalidos("El código del recibo no es válido.")
        self._codigo = valor

    def nuevo_codigo(self):
        """Por si el código al azar ya existía (casi imposible): se sortea otro."""
        self.codigo = self.generar_codigo()

    @classmethod
    def desde_carrito(cls, usuario, carrito, metodo_pago):
        items = [
            ItemPedido(i.producto.id, i.producto.nombre, i.producto.precio, i.cantidad)
            for i in carrito.items
        ]
        return cls(usuario.id, items, metodo_pago.CLAVE, nombre_cliente=usuario.nombre)

    @property
    def id(self):
        return self._id

    def asignar_id(self, nuevo_id):
        if self._id is not None:
            raise ValueError("El pedido ya tiene id.")
        self._id = nuevo_id

    @property
    def items(self):
        return list(self._items)

    @property
    def estado(self):
        return self._estado

    @property
    def total(self):
        return round(sum(i.subtotal for i in self._items), 2)

    @property
    def cantidad_total(self):
        return sum(i.cantidad for i in self._items)

    def pertenece_a(self, usuario):
        return usuario is not None and usuario.id == self.usuario_id

    def puede_cancelarse(self):
        return self._estado == EstadoPedido.PENDIENTE

    def cancelar(self):
        if not self.puede_cancelarse():
            raise PedidoNoCancelable("Este pedido ya no se puede cancelar.")
        self._estado = EstadoPedido.CANCELADO

    def marcar_entregado(self):
        self._cambiar_a(EstadoPedido.ENTREGADO)

    def marcar_no_recogido(self):
        self._cambiar_a(EstadoPedido.NO_RECOGIDO)

    def _cambiar_a(self, nuevo):
        """Solo un pedido pendiente puede pasar a entregado o no recogido."""
        if self._estado.es_final:
            raise CambioEstadoInvalido(
                f"El pedido {self.codigo} ya está «{self._estado.texto.lower()}»; "
                f"no se puede marcar como «{nuevo.texto.lower()}».")
        self._estado = nuevo
