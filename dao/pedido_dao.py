"""DAO de las tablas pedidos y detalle_pedido."""

from dao.base import DAO
from modelos.excepciones import InventarioInsuficiente
from modelos.pedido import EstadoPedido, ItemPedido, Pedido


class PedidoDAO(DAO):
    MENSAJE_EN_USO = "No se puede eliminar el pedido."
    MENSAJE_NO_ENCONTRADO = "No encontramos ese pedido."

    _SELECT = """SELECT p.*, u.nombre AS nombre_cliente
                 FROM pedidos p JOIN usuarios u ON u.id = p.usuario_id"""

    def _a_objeto(self, fila):
        """fila trae los datos del pedido y la lista 'items' ya cargada."""
        if fila is None:
            return None
        return Pedido(
            usuario_id=fila["usuario_id"],
            items=fila["items"],
            metodo_pago=fila["metodo_pago"],
            estado=EstadoPedido(fila["estado"]),
            fecha=fila["fecha"],
            id=fila["id"],
            nombre_cliente=fila["nombre_cliente"],
        )

    def _cargar(self, con, fila):
        """Junta el pedido con sus líneas de detalle_pedido."""
        datos = dict(fila)
        datos["items"] = [
            ItemPedido(f["producto_id"], f["nombre_producto"], f["precio_unitario"], f["cantidad"])
            for f in con.execute("SELECT * FROM detalle_pedido WHERE pedido_id = ? ORDER BY id",
                                 (fila["id"],)).fetchall()
        ]
        return self._a_objeto(datos)

    # ---------- C ----------
    def insertar(self, pedido):
        """Guarda el pedido y descuenta el inventario en UNA sola transacción.

        Si un producto ya no tiene suficientes existencias (por ejemplo, otra
        estudiante compró el último un segundo antes), se lanza
        InventarioInsuficiente y no se guarda nada: ni el pedido ni los descuentos.
        """
        with self._conexion() as con:
            cursor = con.execute(
                "INSERT INTO pedidos (usuario_id, fecha, estado, metodo_pago, total) "
                "VALUES (?, ?, ?, ?, ?)",
                (pedido.usuario_id, pedido.fecha, pedido.estado.value,
                 pedido.metodo_pago, pedido.total),
            )
            pedido_id = cursor.lastrowid
            for item in pedido.items:
                # Solo descuenta si alcanza: así nunca quedan existencias negativas
                actualizado = con.execute(
                    "UPDATE productos SET existencias = existencias - ? "
                    "WHERE id = ? AND activo = 1 AND existencias >= ?",
                    (item.cantidad, item.producto_id, item.cantidad),
                )
                if actualizado.rowcount == 0:
                    fila = con.execute("SELECT existencias FROM productos WHERE id = ?",
                                       (item.producto_id,)).fetchone()
                    raise InventarioInsuficiente(item.nombre_producto,
                                                 fila["existencias"] if fila else 0)
                con.execute(
                    "INSERT INTO detalle_pedido "
                    "(pedido_id, producto_id, nombre_producto, precio_unitario, cantidad) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (pedido_id, item.producto_id, item.nombre_producto,
                     item.precio_unitario, item.cantidad),
                )
        pedido.asignar_id(pedido_id)
        return pedido

    # ---------- R ----------
    def buscar_por_id(self, id):
        with self._conexion() as con:
            fila = con.execute(self._SELECT + " WHERE p.id = ?", (id,)).fetchone()
            return self._cargar(con, fila) if fila else None

    def listar(self, usuario_id=None, estado=None):
        """Todos los pedidos, o solo los de un estudiante y/o de un estado."""
        condiciones, parametros = [], []
        if usuario_id is not None:
            condiciones.append("p.usuario_id = ?")
            parametros.append(usuario_id)
        if estado:
            condiciones.append("p.estado = ?")
            parametros.append(estado)
        sql = self._SELECT
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY p.id DESC"
        with self._conexion() as con:
            return [self._cargar(con, f) for f in con.execute(sql, parametros).fetchall()]

    def contar(self, estado=None):
        with self._conexion() as con:
            if estado:
                return con.execute("SELECT COUNT(*) FROM pedidos WHERE estado = ?",
                                   (estado,)).fetchone()[0]
            return con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

    # ---------- U ----------
    def actualizar(self, pedido):
        """Guarda el estado del pedido."""
        with self._conexion() as con:
            cursor = con.execute("UPDATE pedidos SET estado = ? WHERE id = ?",
                                 (pedido.estado.value, pedido.id))
            self._confirmar_afectadas(cursor)
        return pedido

    def cancelar(self, pedido):
        """Guarda el pedido como cancelado y devuelve sus productos al inventario.

        Las dos cosas van en la misma transacción.
        """
        with self._conexion() as con:
            cursor = con.execute("UPDATE pedidos SET estado = ? WHERE id = ?",
                                 (pedido.estado.value, pedido.id))
            self._confirmar_afectadas(cursor)
            for item in pedido.items:
                con.execute("UPDATE productos SET existencias = existencias + ? WHERE id = ?",
                            (item.cantidad, item.producto_id))
        return pedido

    # ---------- D ----------
    def eliminar(self, id):
        """Borra el pedido; sus líneas se borran solas (ON DELETE CASCADE)."""
        with self._conexion() as con:
            cursor = con.execute("DELETE FROM pedidos WHERE id = ?", (id,))
            self._confirmar_afectadas(cursor)
