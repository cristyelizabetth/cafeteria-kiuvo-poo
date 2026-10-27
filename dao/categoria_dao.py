"""DAO de la tabla categorias."""

from dao.base import DAO
from modelos.categoria import Categoria
from modelos.excepciones import DatosInvalidos


class CategoriaDAO(DAO):
    MENSAJE_DUPLICADO = "Ya existe una categoría con ese nombre para ese tipo de producto."
    MENSAJE_EN_USO = "No se puede eliminar la categoría porque hay productos que la usan."
    MENSAJE_NO_ENCONTRADO = "La categoría no existe."

    def _a_objeto(self, fila):
        if fila is None:
            return None
        return Categoria(fila["nombre"], fila["tipo"], id=fila["id"])

    # ---------- C ----------
    def insertar(self, categoria):
        with self._conexion() as con:
            cursor = con.execute("INSERT INTO categorias (nombre, tipo) VALUES (?, ?)",
                                 (categoria.nombre, categoria.tipo))
        categoria.asignar_id(cursor.lastrowid)
        return categoria

    def asegurar(self, clases_producto):
        """Crea las categorías oficiales de cada clase de producto si aún no existen.

        La lista oficial está en cada clase (Almuerzo.CATEGORIAS, ProductoTienda.CATEGORIAS).
        INSERT OR IGNORE no repite las que ya están.
        """
        with self._conexion() as con:
            for clase in clases_producto:
                for nombre in clase.CATEGORIAS:
                    con.execute("INSERT OR IGNORE INTO categorias (nombre, tipo) VALUES (?, ?)",
                                (nombre, clase.TIPO))

    # ---------- R ----------
    def buscar_por_id(self, id):
        with self._conexion() as con:
            fila = con.execute("SELECT * FROM categorias WHERE id = ?", (id,)).fetchone()
        return self._a_objeto(fila)

    def listar(self, tipo=None):
        with self._conexion() as con:
            if tipo:
                filas = con.execute("SELECT * FROM categorias WHERE tipo = ? ORDER BY id",
                                    (tipo,)).fetchall()
            else:
                filas = con.execute("SELECT * FROM categorias ORDER BY tipo, id").fetchall()
        return [self._a_objeto(f) for f in filas]

    @staticmethod
    def buscar_id(con, nombre, tipo):
        """id de la categoría con ese nombre y tipo.

        Recibe una conexión ya abierta para que ProductoDAO lo use dentro de
        su misma transacción.
        """
        fila = con.execute("SELECT id FROM categorias WHERE nombre = ? AND tipo = ?",
                           (nombre, tipo)).fetchone()
        if fila is None:
            raise DatosInvalidos(f"La categoría «{nombre}» no existe.")
        return fila["id"]

    # ---------- U ----------
    def actualizar(self, categoria):
        with self._conexion() as con:
            cursor = con.execute("UPDATE categorias SET nombre = ? WHERE id = ?",
                                 (categoria.nombre, categoria.id))
            self._confirmar_afectadas(cursor)
        return categoria

    # ---------- D ----------
    def eliminar(self, id):
        with self._conexion() as con:
            cursor = con.execute("DELETE FROM categorias WHERE id = ?", (id,))
            self._confirmar_afectadas(cursor)
