"""DAO de las tablas productos, almuerzos y productos_tienda."""

from dao.base import DAO
from dao.categoria_dao import CategoriaDAO
from modelos.producto import Producto


class ProductoDAO(DAO):
    """Cada producto se reparte en dos tablas:

    - productos          → datos comunes (clase Producto)
    - almuerzos          → datos propios de Almuerzo        } la tabla la indica
    - productos_tienda   → datos propios de ProductoTienda  } TABLA_DETALLE
    y el nombre de su categoría está en la tabla categorias.
    """

    MENSAJE_DUPLICADO = "Ya existe un producto con ese nombre."
    MENSAJE_EN_USO = ("Este producto ya aparece en pedidos de estudiantes, así que no se puede "
                      "eliminar sin borrar ese historial. Puedes ocultarlo para que deje de verse.")
    MENSAJE_NO_ENCONTRADO = "Ese producto no existe."

    # Une las tablas para reconstruir cada producto completo.
    # LEFT JOIN: cada producto tiene fila en UNA de las dos tablas de detalle.
    _SELECT = """
        SELECT p.id, p.tipo, p.nombre, p.descripcion, p.precio, p.existencias, p.activo,
               c.nombre AS categoria,
               a.incluye,
               t.presentacion
        FROM productos p
        JOIN categorias c            ON c.id = p.categoria_id
        LEFT JOIN almuerzos a        ON a.producto_id = p.id
        LEFT JOIN productos_tienda t ON t.producto_id = p.id
    """

    def _a_objeto(self, fila):
        if fila is None:
            return None
        # Fábrica: según el tipo crea un Almuerzo o un ProductoTienda
        return Producto.construir(
            fila["tipo"],
            id=fila["id"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"],
            categoria=fila["categoria"],
            precio=fila["precio"],
            existencias=fila["existencias"],
            activo=bool(fila["activo"]),
            incluye=fila["incluye"],
            presentacion=fila["presentacion"],
        )

    # ---------- C ----------
    def insertar(self, producto):
        with self._conexion() as con:
            categoria_id = CategoriaDAO.buscar_id(con, producto.categoria, producto.tipo)
            cursor = con.execute(
                """INSERT INTO productos (tipo, nombre, descripcion, categoria_id, precio,
                   existencias, activo) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (producto.tipo, producto.nombre, producto.descripcion, categoria_id,
                 producto.precio, producto.existencias, int(producto.activo)),
            )
            producto.asignar_id(cursor.lastrowid)
            self._guardar_detalle(con, producto)
        return producto

    # ---------- R ----------
    def buscar_por_id(self, id):
        with self._conexion() as con:
            fila = con.execute(self._SELECT + " WHERE p.id = ?", (id,)).fetchone()
        return self._a_objeto(fila)

    def listar(self, tipo=None, categoria=None, solo_disponibles=False):
        """Lista productos con filtros opcionales.

        solo_disponibles=True es la vista del estudiante (activos y con existencias);
        False es la vista del administrador (todo el inventario).
        """
        condiciones, parametros = [], []
        if tipo:
            condiciones.append("p.tipo = ?")
            parametros.append(tipo)
        if categoria:
            condiciones.append("c.nombre = ?")
            parametros.append(categoria)
        if solo_disponibles:
            condiciones.append("p.activo = 1 AND p.existencias > 0")
        sql = self._SELECT
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY p.tipo, c.id, p.nombre"
        with self._conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return [self._a_objeto(f) for f in filas]

    def existe_nombre(self, nombre, tipo, excluir_id=None):
        """¿Ya hay otro producto de ese tipo con ese nombre? (sin importar mayúsculas)"""
        with self._conexion() as con:
            fila = con.execute(
                "SELECT id FROM productos WHERE tipo = ? AND nombre = ? COLLATE NOCASE "
                "AND id IS NOT ?",
                (tipo, nombre, excluir_id),
            ).fetchone()
        return fila is not None

    def contar(self):
        with self._conexion() as con:
            return con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]

    # ---------- U ----------
    def actualizar(self, producto):
        """Las dos tablas se actualizan en la misma transacción: o ambas o ninguna."""
        with self._conexion() as con:
            categoria_id = CategoriaDAO.buscar_id(con, producto.categoria, producto.tipo)
            cursor = con.execute(
                """UPDATE productos SET nombre = ?, descripcion = ?, categoria_id = ?,
                   precio = ?, existencias = ?, activo = ? WHERE id = ?""",
                (producto.nombre, producto.descripcion, categoria_id,
                 producto.precio, producto.existencias, int(producto.activo), producto.id),
            )
            self._confirmar_afectadas(cursor)
            self._guardar_detalle(con, producto)
        return producto

    # ---------- D ----------
    def eliminar(self, id):
        """Borra el producto. Su fila de almuerzos/productos_tienda se borra sola
        (ON DELETE CASCADE). Si ya aparece en algún pedido, la llave foránea de
        detalle_pedido lo impide y se lanza RegistroEnUso."""
        with self._conexion() as con:
            cursor = con.execute("DELETE FROM productos WHERE id = ?", (id,))
            self._confirmar_afectadas(cursor)

    # ---------- Ayudante ----------
    @staticmethod
    def _guardar_detalle(con, producto):
        """Guarda los datos propios del tipo en su tabla (polimorfismo).

        El nombre de la tabla y de las columnas sale de la propia clase
        (TABLA_DETALLE y datos_extra()), nunca de lo que escribe el usuario;
        los VALORES sí van como parámetros (?).
        """
        tablas_validas = {clase.TABLA_DETALLE for clase in Producto.tipos()}
        tabla = producto.TABLA_DETALLE
        if tabla not in tablas_validas:
            raise ValueError(f"Tabla de detalle desconocida: {tabla}")
        datos = producto.datos_extra()
        columnas = ", ".join(datos)
        signos = ", ".join("?" for _ in datos)
        actualizar = ", ".join(f"{col} = excluded.{col}" for col in datos)
        con.execute(
            f"INSERT INTO {tabla} (producto_id, {columnas}) VALUES (?, {signos}) "
            f"ON CONFLICT (producto_id) DO UPDATE SET {actualizar}",
            (producto.id, *datos.values()),
        )
