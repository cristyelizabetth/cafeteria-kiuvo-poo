-- Esquema de la base de datos de Cafetería Kiuvo (SQLite)
-- Copia de BaseDatos.ESQUEMA (base_datos.py): ahí es donde el programa crea las tablas.
-- Las llaves foráneas se activan en cada conexión con: PRAGMA foreign_keys = ON;

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
    imagen        TEXT,          -- nombre del archivo de la foto (NULL = ilustración de la categoría)
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

-- No se permiten dos productos del mismo tipo con el mismo nombre (sin importar mayúsculas)
CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_nombre_unico
    ON productos (tipo, nombre COLLATE NOCASE);
