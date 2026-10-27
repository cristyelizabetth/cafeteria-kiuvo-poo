# Cambios: normalización de la base de datos

Rama: `normalizar-bd`

> **Nota:** después de este cambio, los repositorios (`repositorios.py`) se convirtieron en la capa DAO (carpeta `dao/`). `RepositorioCategorias` ahora es `CategoriaDAO` y `RepositorioProductos` es `ProductoDAO`. Ver `CAMBIOS_RUBRICA.md`.

Responde a la revisión del profesor:

> **Puntos de mejora:** Conectar base de datos. Agregar validaciones y normalizar modelo (separar tablas).

| Recomendación | Cómo queda |
|---|---|
| Conectar base de datos | SQLite (`instancia/kiuvo.db`). Todo se guarda ahí: usuarios, categorías, productos, pedidos y su detalle. |
| Agregar validaciones | En tres niveles: formularios (`servicios.py`), clases (propiedades de `Producto`, `Usuario`, `Pedido`) y base de datos (`CHECK`, `UNIQUE`, llaves foráneas). Esta rama agrega una más: la base rechaza un producto en una categoría de otro tipo. |
| Normalizar / separar tablas | De 4 a 7 tablas. Ver abajo. |

## Antes y después

**Antes (4 tablas):**

```
productos
id | tipo     | nombre  | categoria      | precio | ... | incluye | presentacion
1  | almuerzo | Pollo   | Plato del día  | 3.50   | ... | Arroz   | NULL          ← columna vacía
2  | tienda   | Agua    | Bebidas        | 0.75   | ... | NULL    | 600 ml        ← columna vacía
3  | tienda   | Jugo    | Bebidas        | 1.25   | ... | NULL    | 350 ml        ← "Bebidas" repetido
```

**Después (7 tablas):**

```
categorias               productos                                   almuerzos
id | nombre     | tipo   id | tipo     | nombre | categoria_id | ...    producto_id | incluye
1  | Plato d.d. | alm.   1  | almuerzo | Pollo  | 1            |        1           | Arroz
4  | Bebidas    | tienda 2  | tienda   | Agua   | 4            |
                         3  | tienda   | Jugo   | 4            |      productos_tienda
                                                                     producto_id | presentacion
                                                                     2           | 600 ml
                                                                     3           | 350 ml
```

- **"Bebidas" se escribe una sola vez**, en `categorias`. Los productos solo guardan el número (`categoria_id`).
- **Ya no hay columnas vacías.** Cada tabla de detalle tiene solo las columnas de su tipo.
- La estructura refleja la herencia de las clases: `productos` = clase `Producto` (lo común), `almuerzos` = `Almuerzo`, `productos_tienda` = `ProductoTienda`.

Diagrama actualizado: `docs/diagrama_base_datos.png`.

## Archivos que cambiaron

| Archivo | Cambio |
|---|---|
| `base_datos.py` | Tablas nuevas `categorias`, `almuerzos` y `productos_tienda`. `productos` cambia la columna `categoria` (texto) por `categoria_id` y pierde `incluye` y `presentacion`. Llave foránea doble `(categoria_id, tipo)` para que la categoría sea del mismo tipo que el producto. **Actualización automática:** si encuentra una base de la versión anterior, la convierte sin perder productos ni pedidos. |
| `repositorios.py` | Nueva clase **`RepositorioCategorias`**. `RepositorioProductos` lee con `JOIN` (une las 4 tablas de productos) y al guardar escribe en `productos` y en la tabla de detalle de su tipo, en una sola transacción. |
| `modelos/producto.py` | Cada clase hija dice en qué tabla van sus datos propios (`TABLA_DETALLE`) y `datos_extra()` devuelve solo sus columnas. Nuevo método `Producto.tipos()`. |
| `datos_iniciales.py` | Crea las categorías oficiales al arrancar, sin repetirlas. |
| `app.py`, `contenedor.py` | Crean y guardan el `RepositorioCategorias`. |
| `pruebas/test_cafeteria.py` | 6 pruebas nuevas (32 en total): tablas separadas, categorías sin repetir, cada producto con su detalle, edición, categoría de otro tipo rechazada y actualización de una base vieja. |
| `docs/` | Diagramas de base de datos y de clases, `BASE_DE_DATOS.md`, `CLASES.md` y este archivo. `README.md` también. |

**No cambiaron** las páginas, el diseño, las rutas ni la seguridad: el sitio se ve y funciona igual. Solo cambió cómo se guardan los datos por dentro. Eso es justamente una ventaja de tener los repositorios separados: el resto del código no se enteró del cambio.

## Si ya tenían una base de datos creada

No hay que borrar nada. La primera vez que ejecuten `py app.py` con esta versión, `BaseDatos` detecta la base vieja y la actualiza:

1. Crea las tablas nuevas.
2. Copia cada categoría distinta a `categorias`.
3. Copia los productos con su `categoria_id`, conservando sus `id` para que los pedidos viejos sigan apuntando al producto correcto.
4. Pasa `incluye` a `almuerzos` y `presentacion` a `productos_tienda`.
5. Borra la tabla vieja.

Todo va en una transacción: si algo falla, la base queda como estaba. La versión se guarda dentro del archivo (`PRAGMA user_version = 2`) para no repetir el proceso.

## Cómo explicarlo en la defensa

> "En la revisión nos pidieron normalizar. Antes la categoría era texto repetido en cada producto, y almuerzos y productos de tienda compartían una tabla con columnas que quedaban vacías. Ahora las categorías están en su propia tabla y cada producto la referencia con una llave foránea. Además, los datos propios de cada tipo están en tablas separadas, `almuerzos` y `productos_tienda`, que reflejan la herencia de nuestras clases: `productos` tiene lo común, como la clase padre `Producto`, y cada tabla hija lo propio. Para leer un producto completo se unen con `JOIN`. Como todo el SQL está en los repositorios, el resto del programa no tuvo que cambiar."
