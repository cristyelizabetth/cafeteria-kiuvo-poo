"""Pedidos: un Pedido contiene varios ItemPedido (composición)."""

from datetime import datetime
from enum import Enum

from modelos.excepciones import DatosInvalidos, PedidoNoCancelable


class EstadoPedido(Enum):
    PENDIENTE = "pendiente"   # pagado o por pagar en caja, esperando ser retirado
    CANCELADO = "cancelado"

    @property
    def texto(self):
        return {"pendiente": "Pendiente de retiro", "cancelado": "Cancelado"}[self.value]


class ItemPedido:
    """Una línea del pedido.

    Guarda una copia del nombre y del precio en el momento de la compra:
    si después el admin cambia el precio, el pedido viejo no cambia.
    """

    def __init__(self, producto_id, nombre_producto, precio_unitario, cantidad):
        self.producto_id = producto_id
        self.nombre_producto = nombre_producto
        self.precio_unitario = round(float(precio_unitario), 2)
        self.cantidad = int(cantidad)

    @property
    def subtotal(self):
        return round(self.precio_unitario * self.cantidad, 2)


class Pedido:
    def __init__(self, usuario_id, items, metodo_pago, estado=EstadoPedido.PENDIENTE,
                 fecha=None, id=None, nombre_cliente=None):
        if not items:
            raise DatosInvalidos("Un pedido debe tener al menos un producto.")
        self._id = id
        self.usuario_id = usuario_id
        self._items = list(items)
        self.metodo_pago = metodo_pago
        self._estado = estado
        self.fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M")
        self.nombre_cliente = nombre_cliente

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
