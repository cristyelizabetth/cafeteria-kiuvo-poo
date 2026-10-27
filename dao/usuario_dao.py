"""DAO de la tabla usuarios."""

from dao.base import DAO
from modelos.usuario import Usuario


class UsuarioDAO(DAO):
    MENSAJE_DUPLICADO = "Ya existe una cuenta con ese correo."
    MENSAJE_EN_USO = "No se puede eliminar la cuenta porque tiene pedidos registrados."
    MENSAJE_NO_ENCONTRADO = "La cuenta no existe."

    def _a_objeto(self, fila):
        if fila is None:
            return None
        # Fábrica: según el rol guardado crea un Estudiante o un Administrador
        return Usuario.construir(
            fila["rol"],
            id=fila["id"],
            nombre=fila["nombre"],
            correo=fila["correo"],
            password_hash=fila["password_hash"],
            pregunta_seguridad=fila["pregunta_seguridad"],
            respuesta_hash=fila["respuesta_hash"],
        )

    # ---------- C ----------
    def insertar(self, usuario):
        with self._conexion() as con:
            cursor = con.execute(
                """INSERT INTO usuarios
                   (nombre, correo, password_hash, rol, pregunta_seguridad, respuesta_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (usuario.nombre, usuario.correo, usuario.password_hash, usuario.rol,
                 usuario.pregunta_seguridad, usuario.respuesta_hash),
            )
        usuario.asignar_id(cursor.lastrowid)
        return usuario

    # ---------- R ----------
    def buscar_por_id(self, id):
        with self._conexion() as con:
            fila = con.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
        return self._a_objeto(fila)

    def buscar_por_correo(self, correo):
        with self._conexion() as con:
            fila = con.execute("SELECT * FROM usuarios WHERE correo = ?",
                               (Usuario.normalizar_correo(correo),)).fetchone()
        return self._a_objeto(fila)

    def existe_correo(self, correo):
        return self.buscar_por_correo(correo) is not None

    def listar(self, rol=None):
        with self._conexion() as con:
            if rol:
                filas = con.execute("SELECT * FROM usuarios WHERE rol = ? ORDER BY nombre",
                                    (rol,)).fetchall()
            else:
                filas = con.execute("SELECT * FROM usuarios ORDER BY nombre").fetchall()
        return [self._a_objeto(f) for f in filas]

    def contar(self, rol=None):
        with self._conexion() as con:
            if rol:
                return con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = ?",
                                   (rol,)).fetchone()[0]
            return con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    # ---------- U ----------
    def actualizar(self, usuario):
        with self._conexion() as con:
            cursor = con.execute(
                """UPDATE usuarios SET nombre = ?, password_hash = ?,
                   pregunta_seguridad = ?, respuesta_hash = ? WHERE id = ?""",
                (usuario.nombre, usuario.password_hash, usuario.pregunta_seguridad,
                 usuario.respuesta_hash, usuario.id),
            )
            self._confirmar_afectadas(cursor)
        return usuario

    # ---------- D ----------
    def eliminar(self, id):
        with self._conexion() as con:
            cursor = con.execute("DELETE FROM usuarios WHERE id = ?", (id,))
            self._confirmar_afectadas(cursor)
