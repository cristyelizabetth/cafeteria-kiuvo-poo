"""DAO de las tablas pedidos y detalle_pedido."""

from dao.base import DAO
from modelos.excepciones import InventarioInsuficiente
from modelos.pedido import EstadoPedido, ItemPedido, Pedido
from modelos.reporte import LineaReporte, ReporteMensual


class PedidoDAO(DAO):
    MENSAJE_DUPLICADO = "Ya existe un pedido con ese código de recibo."
    MENSAJE_EN_USO = "No se puede eliminar el pedido."
    MENSAJE_NO_ENCONTRADO = "No encontramos ese pedido."
    MENSAJE_REFERENCIA = "El pedido hace referencia a un estudiante o producto que no existe."

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
            codigo=fila["codigo"],
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
                "INSERT INTO pedidos (codigo, usuario_id, fecha, estado, metodo_pago, total) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pedido.codigo, pedido.usuario_id, pedido.fecha, pedido.estado.value,
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

    def buscar_por_codigo(self, codigo):
        """El pedido con ese código de recibo (el que el estudiante muestra en la barra)."""
        with self._conexion() as con:
            fila = con.execute(self._SELECT + " WHERE p.codigo = ?", (codigo,)).fetchone()
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

    # ---------- Consulta propia del negocio: reporte mensual ----------
    def reporte_mensual(self, anio, mes):
        """Lo que se vendió en un mes, producto por producto (para los cuadros de fin de mes).

        Cuenta como venta todo pedido que NO fue cancelado. Usa GROUP BY para
        sumar las unidades y el dinero de cada producto, y devuelve un objeto
        ReporteMensual (no filas sueltas).
        """
        anio, mes = ReporteMensual.validar_mes(anio, mes)
        desde, hasta = ReporteMensual.rango_fechas(anio, mes)
        with self._conexion() as con:
            filas = con.execute(
                """SELECT d.nombre_producto               AS producto,
                          pr.tipo                         AS tipo,
                          SUM(d.cantidad)                 AS unidades,
                          SUM(d.cantidad * d.precio_unitario) AS total
                   FROM detalle_pedido d
                   JOIN pedidos p        ON p.id = d.pedido_id
                   LEFT JOIN productos pr ON pr.id = d.producto_id
                   WHERE p.estado <> 'cancelado' AND p.fecha >= ? AND p.fecha < ?
                   GROUP BY d.producto_id, d.nombre_producto
                   ORDER BY total DESC, producto""",
                (desde, hasta),
            ).fetchall()
            por_estado = con.execute(
                """SELECT estado, COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS dinero
                   FROM pedidos
                   WHERE fecha >= ? AND fecha < ?
                   GROUP BY estado""",
                (desde, hasta),
            ).fetchall()
        lineas = [LineaReporte(f["producto"], f["tipo"], f["unidades"], f["total"]) for f in filas]
        return ReporteMensual(anio, mes, lineas,
                              {f["estado"]: (f["cantidad"], f["dinero"]) for f in por_estado})

    # ---------- U ----------
    def actualizar(self, pedido):
        """Guarda el estado del pedido (por ejemplo, entregado o no recogido)."""
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
        with self._conexion(borrando=True) as con:
            cursor = con.execute("DELETE FROM pedidos WHERE id = ?", (id,))
            self._confirmar_afectadas(cursor)
