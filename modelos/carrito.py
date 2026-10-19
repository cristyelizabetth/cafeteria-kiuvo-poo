"""Carrito de compras: un Carrito contiene varios ItemCarrito (composición)."""

from modelos.excepciones import DatosInvalidos, InventarioInsuficiente, ProductoNoDisponible


class ItemCarrito:
    """Un producto dentro del carrito con su cantidad."""

    def __init__(self, producto, cantidad):
        if cantidad < 1:
            raise DatosInvalidos("La cantidad debe ser al menos 1.")
        self.producto = producto
        self.cantidad = cantidad

    @property
    def subtotal(self):
        return round(self.producto.precio * self.cantidad, 2)


class Carrito:
    """Carrito del estudiante.

    En la sesión del navegador solo se guarda {id_producto: cantidad}
    (método a_dict). En cada petición se reconstruye con los datos
    actuales de la base de datos (método desde_dict), así los precios y
    existencias siempre están al día.
    """

    MAXIMO_POR_PRODUCTO = 20

    def __init__(self):
        self._items = {}   # id_producto -> ItemCarrito
        self.avisos = []   # mensajes si algo cambió al reconstruir el carrito

    # ---------- Operaciones ----------
    def agregar(self, producto, cantidad=1):
        if not producto.esta_disponible():
            raise ProductoNoDisponible(f"«{producto.nombre}» ya no está disponible.")
        actual = self.cantidad_de(producto.id)
        self.cambiar_cantidad(producto, actual + cantidad)

    def cambiar_cantidad(self, producto, cantidad):
        if cantidad <= 0:
            self.quitar(producto.id)
            return
        if cantidad > self.MAXIMO_POR_PRODUCTO:
            raise DatosInvalidos(
                f"Puedes llevar como máximo {self.MAXIMO_POR_PRODUCTO} de cada producto."
            )
        if not producto.hay_suficiente(cantidad):
            raise InventarioInsuficiente(producto.nombre, producto.existencias)
        self._items[producto.id] = ItemCarrito(producto, cantidad)

    def quitar(self, producto_id):
        self._items.pop(producto_id, None)

    def vaciar(self):
        self._items.clear()

    # ---------- Consultas ----------
    def cantidad_de(self, producto_id):
        item = self._items.get(producto_id)
        return item.cantidad if item else 0

    @property
    def items(self):
        return list(self._items.values())

    @property
    def total(self):
        return round(sum(item.subtotal for item in self._items.values()), 2)

    @property
    def cantidad_total(self):
        return sum(item.cantidad for item in self._items.values())

    def esta_vacio(self):
        return not self._items

    # ---------- Guardar en / leer de la sesión ----------
    def a_dict(self):
        return {str(pid): item.cantidad for pid, item in self._items.items()}

    @classmethod
    def desde_dict(cls, datos, repositorio_productos):
        carrito = cls()
        for pid_texto, cantidad in (datos or {}).items():
            producto = repositorio_productos.buscar_por_id(int(pid_texto))
            if producto is None or not producto.esta_disponible():
                nombre = producto.nombre if producto else "Un producto"
                carrito.avisos.append(f"{nombre} ya no está disponible y se quitó del carrito.")
                continue
            if cantidad > producto.existencias:
                carrito.avisos.append(
                    f"Solo quedan {producto.existencias} de «{producto.nombre}»; "
                    "se ajustó la cantidad."
                )
                cantidad = producto.existencias
            carrito._items[producto.id] = ItemCarrito(producto, cantidad)
        return carrito
