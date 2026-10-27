"""Conexión con la base de datos SQLite y creación de las tablas."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class BaseDatos:
    """Se encarga SOLO de conectarse a SQLite y crear las tablas.

    No sabe nada de estudiantes ni de productos: eso lo hacen los DAO (carpeta dao/).
    """

    # Número de versión del diseño de las tablas. Se guarda dentro del archivo
    # .db (PRAGMA user_version) para saber si una base vieja necesita actualizarse.
    #   1 = versión original (categoría como texto, almuerzos y tienda en una sola tabla)
    #   2 = versión normalizada (tablas categorias, almuerzos y productos_tienda)
    VERSION_ESQUEMA = 2

    ESQUEMA = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre              TEXT    NOT NULL,
        correo              TEXT    NOT NULL UNIQUE,
        password_hash       TEXT    NOT NULL,
        rol                 TEXT    NOT NULL CHECK (rol IN ('estudiante', 'administrador')),
        pregunta_seguridad  TEXT    NOT NULL,
        respuesta_hash      TEXT    NOT NULL,
        creado_en           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );

    -- Cada categoría se escribe UNA sola vez; los productos la señalan por su id.
    CREATE TABLE IF NOT EXISTS categorias (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre  TEXT    NOT NULL,
        tipo    TEXT    NOT NULL CHECK (tipo IN ('almuerzo', 'tienda')),
        UNIQUE (nombre, tipo),
        UNIQUE (id, tipo)        -- permite que productos revise que el tipo coincida
    );

    -- Datos COMUNES a todos los productos (lo que tiene la clase Producto).
    CREATE TABLE IF NOT EXISTS productos (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo          TEXT    NOT NULL CHECK (tipo IN ('almuerzo', 'tienda')),
        nombre        TEXT    NOT NULL,
        descripcion   TEXT    NOT NULL DEFAULT '',
        categoria_id  INTEGER NOT NULL,
        precio        REAL    NOT NULL CHECK (precio >= 0),
        existencias   INTEGER NOT NULL CHECK (existencias >= 0),
        activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        -- La categoría debe existir Y ser del mismo tipo que el producto:
        -- un almuerzo no puede quedar en la categoría "Bebidas".
        FOREIGN KEY (categoria_id, tipo) REFERENCES categorias (id, tipo)
    );

    -- Datos PROPIOS de cada clase hija (Almuerzo y ProductoTienda).
    -- producto_id es a la vez llave primaria y foránea: relación uno a uno.
    CREATE TABLE IF NOT EXISTS almuerzos (
        producto_id  INTEGER PRIMARY KEY REFERENCES productos (id) ON DELETE CASCADE,
        incluye      TEXT    NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS productos_tienda (
        producto_id   INTEGER PRIMARY KEY REFERENCES productos (id) ON DELETE CASCADE,
        presentacion  TEXT    NOT NULL DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS pedidos (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id   INTEGER NOT NULL REFERENCES usuarios(id),
        fecha        TEXT    NOT NULL,
        estado       TEXT    NOT NULL CHECK (estado IN ('pendiente', 'cancelado')),
        metodo_pago  TEXT    NOT NULL,
        total        REAL    NOT NULL CHECK (total >= 0)
    );

    CREATE TABLE IF NOT EXISTS detalle_pedido (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id        INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
        producto_id      INTEGER NOT NULL REFERENCES productos(id),
        nombre_producto  TEXT    NOT NULL,
        precio_unitario  REAL    NOT NULL,
        cantidad         INTEGER NOT NULL CHECK (cantidad > 0)
    );

    CREATE INDEX IF NOT EXISTS idx_pedidos_usuario    ON pedidos(usuario_id);
    CREATE INDEX IF NOT EXISTS idx_detalle_pedido     ON detalle_pedido(pedido_id);
    CREATE INDEX IF NOT EXISTS idx_productos_tipo     ON productos(tipo, categoria_id);
    """

    # No puede haber dos productos del mismo tipo con el mismo nombre
    # (COLLATE NOCASE: "Brownie" y "brownie" cuentan como iguales).
    INDICE_NOMBRE_UNICO = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_nombre_unico
        ON productos (tipo, nombre COLLATE NOCASE)
    """

    def __init__(self, ruta):
        self._ruta = str(ruta)

    @property
    def ruta(self):
        return self._ruta

    def _conectar(self):
        conexion = sqlite3.connect(self._ruta)
        conexion.row_factory = sqlite3.Row          # filas accesibles por nombre: fila["nombre"]
        conexion.execute("PRAGMA foreign_keys = ON")  # SQLite no revisa las llaves foráneas si no se activa
        return conexion

    @contextmanager
    def conexion(self):
        """Abre una conexión, y al terminar guarda (commit) o deshace (rollback).

        Uso:
            with base_datos.conexion() as con:
                con.execute("INSERT ...", (valor1, valor2))

        Si ocurre cualquier error dentro del bloque, NADA de lo que se hizo
        en ese bloque se guarda. Eso es una transacción.
        """
        conexion = self._conectar()
        try:
            yield conexion
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def inicializar(self):
        """Crea la carpeta y las tablas si todavía no existen.

        Si encuentra una base de datos de la versión anterior, la actualiza
        sin perder los productos ni los pedidos.
        """
        if self._ruta != ":memory:":
            Path(self._ruta).parent.mkdir(parents=True, exist_ok=True)
        if self._es_version_1():
            self._migrar_desde_version_1()
        with self.conexion() as con:
            con.executescript(self.ESQUEMA)
            con.execute(f"PRAGMA user_version = {self.VERSION_ESQUEMA}")
        try:
            with self.conexion() as con:
                con.execute(self.INDICE_NOMBRE_UNICO)
        except sqlite3.IntegrityError:
            # Una base vieja ya tenía nombres repetidos: se sigue sin el índice;
            # el servicio de inventario igual revisa los duplicados.
            pass

    # ---------- Actualización de bases de datos viejas ----------
    def _es_version_1(self):
        """True si existe la tabla productos con la columna de texto 'categoria'."""
        with self.conexion() as con:
            columnas = [fila["name"] for fila in con.execute("PRAGMA table_info(productos)")]
        return "categoria" in columnas

    def _migrar_desde_version_1(self):
        """Pasa los datos de la versión 1 a las tablas normalizadas.

        Pasos (todos en una transacción: si algo falla, no se cambia nada):
          1. Crear las tablas nuevas.
          2. Copiar cada categoría distinta a la tabla categorias.
          3. Copiar los productos con su categoria_id (conservando sus id,
             para que los pedidos viejos sigan apuntando al producto correcto).
          4. Copiar 'incluye' a almuerzos y 'presentacion' a productos_tienda.
          5. Borrar la tabla vieja y poner la nueva en su lugar.
        """
        conexion = sqlite3.connect(self._ruta)
        conexion.row_factory = sqlite3.Row
        try:
            # Las llaves foráneas se apagan solo durante el cambio de tablas.
            conexion.execute("PRAGMA foreign_keys = OFF")
            # El BEGIN va dentro del script: executescript() confirma cualquier
            # transacción abierta antes de empezar.
            conexion.executescript("""
                BEGIN;
                CREATE TABLE categorias (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre  TEXT NOT NULL,
                    tipo    TEXT NOT NULL CHECK (tipo IN ('almuerzo', 'tienda')),
                    UNIQUE (nombre, tipo),
                    UNIQUE (id, tipo)
                );
                CREATE TABLE productos_nueva (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo          TEXT    NOT NULL CHECK (tipo IN ('almuerzo', 'tienda')),
                    nombre        TEXT    NOT NULL,
                    descripcion   TEXT    NOT NULL DEFAULT '',
                    categoria_id  INTEGER NOT NULL,
                    precio        REAL    NOT NULL CHECK (precio >= 0),
                    existencias   INTEGER NOT NULL CHECK (existencias >= 0),
                    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
                    FOREIGN KEY (categoria_id, tipo) REFERENCES categorias (id, tipo)
                );
                CREATE TABLE almuerzos (
                    producto_id  INTEGER PRIMARY KEY REFERENCES productos (id) ON DELETE CASCADE,
                    incluye      TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE productos_tienda (
                    producto_id   INTEGER PRIMARY KEY REFERENCES productos (id) ON DELETE CASCADE,
                    presentacion  TEXT NOT NULL DEFAULT ''
                );

                INSERT INTO categorias (nombre, tipo)
                    SELECT DISTINCT categoria, tipo FROM productos;

                INSERT INTO productos_nueva
                    (id, tipo, nombre, descripcion, categoria_id, precio, existencias, activo)
                    SELECT p.id, p.tipo, p.nombre, p.descripcion, c.id, p.precio,
                           p.existencias, p.activo
                    FROM productos p
                    JOIN categorias c ON c.nombre = p.categoria AND c.tipo = p.tipo;

                INSERT INTO almuerzos (producto_id, incluye)
                    SELECT id, COALESCE(incluye, '') FROM productos WHERE tipo = 'almuerzo';
                INSERT INTO productos_tienda (producto_id, presentacion)
                    SELECT id, COALESCE(presentacion, '') FROM productos WHERE tipo = 'tienda';

                DROP TABLE productos;
                ALTER TABLE productos_nueva RENAME TO productos;
            """)
            problemas = conexion.execute("PRAGMA foreign_key_check").fetchall()
            if problemas:
                raise sqlite3.IntegrityError(f"La actualización dejó datos inconsistentes: {problemas}")
            conexion.commit()
        except Exception:
            if conexion.in_transaction:
                conexion.rollback()
            raise
        finally:
            conexion.close()
