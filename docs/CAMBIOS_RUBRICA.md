# Cómo cumple el proyecto la rúbrica final

| Criterio | Puntos | Dónde se ve |
|---|---|---|
| Seguimiento del avance 1 | 20 | Ver la primera tabla de abajo. |
| Persistencia y patrón DAO | 20 | Carpeta `dao/`. Ver "Patrón DAO". |
| Diseño orientado a objetos | 20 | Carpeta `modelos/` y `docs/CLASES.md`. Ver "Diseño orientado a objetos". |
| Funcionalidad y validaciones | 15 | Ver "Validaciones". |
| Diagrama de clases UML | 10 | `docs/diagrama_clases_1_modelo.png`, `_2_dao.png`, `_3_servicios.png`. |
| Defensa individual | 15 | `docs/GUIA_DEFENSA.md`. |

## Seguimiento del avance 1

| Recomendación del avance 1 | Cómo se resolvió | Cómo mostrarlo en la demo |
|---|---|---|
| Conectar base de datos | SQLite, archivo `instancia/kiuvo.db`, 7 tablas | Comprar un almuerzo y ver que bajan las existencias en el inventario del admin |
| Agregar validaciones | En formularios, clases y base de datos (ver abajo) | Intentar crear un producto con precio negativo o con nombre repetido |
| Normalizar modelo (separar tablas) | Tablas `categorias`, `almuerzos` y `productos_tienda` | Mostrar `docs/diagrama_base_datos.png` |

Recomendaciones del pitch: responsive, contraseñas con hash, seguridad, diagrama, conocer las clases y "olvidé mi contraseña". Ver la tabla del `README.md`.

## Patrón DAO

| Lo que pide la rúbrica | Dónde está |
|---|---|
| Interfaz DAO (clase abstracta) | `dao/base.py` → clase `DAO(ABC)` con los métodos abstractos `insertar`, `buscar_por_id`, `listar`, `actualizar` y `eliminar` |
| Su implementación | `UsuarioDAO`, `CategoriaDAO`, `ProductoDAO` y `PedidoDAO` (carpeta `dao/`) |
| Separada de la lógica y de la interfaz | Las rutas (`rutas/`) y los servicios (`servicios.py`) no tienen ni una línea de SQL; solo llaman a métodos de los DAO |
| CRUD completo | Cada DAO tiene las 4 operaciones. En la página, el admin las usa con los productos: **+ Almuerzo** (C), **Inventario** (R), **Editar / Ocultar / Reponer** (U), **Eliminar** (D) |
| Consultas parametrizadas | Todas usan `?` (por ejemplo, `"SELECT * FROM usuarios WHERE correo = ?"`) |
| Transacciones | `DAO._conexion()`: si algo falla se hace `rollback`. Ejemplo: `PedidoDAO.insertar` guarda el pedido, descuenta el inventario y guarda el detalle en una sola transacción |
| Manejo de excepciones | `DAO._conexion()` convierte los errores de SQLite en `RegistroDuplicado`, `RegistroEnUso`, `RegistroNoEncontrado` o `ErrorBaseDatos`, con mensajes claros. Si la base no responde, el sitio muestra una página "Base de datos no disponible" en vez de un error técnico |

## Diseño orientado a objetos

| Lo que pide la rúbrica | Ejemplo |
|---|---|
| Atributos encapsulados con propiedades que validan | `Producto.precio`, `existencias`, `nombre`, `categoria`; `Almuerzo.incluye`; `ProductoTienda.presentacion`; `Categoria.nombre` y `tipo`. `Usuario.__password_hash` es privado y solo cambia con `cambiar_contrasena()` |
| Herencia justificada | `Usuario` → `Estudiante` / `Administrador`: comparten cuenta y contraseña, pero cambian sus permisos. `Producto` → `Almuerzo` / `ProductoTienda`: comparten precio e inventario, pero cada uno tiene un dato propio. `DAO` → 4 DAO: comparten el contrato CRUD y el manejo de errores |
| Polimorfismo justificado | Las rutas llaman `usuario.puede_comprar()` sin preguntar el rol; la plantilla llama `producto.texto_boton()` sin preguntar el tipo; `metodo.procesar(total)` responde distinto según el pago; `producto.datos_extra()` le dice al DAO qué guardar en su tabla |
| Clase abstracta o interfaz con sentido | `Usuario`, `Producto` y `MetodoPago` no tienen sentido "genéricos", así que no se pueden instanciar. `DAO` obliga a que todo DAO tenga el CRUD |

## Validaciones

| Tipo | Ejemplos (con el mensaje que ve el usuario) |
|---|---|
| Entradas vacías | "Escribe tu correo y tu contraseña." · "El nombre no puede estar vacío." · "Escribe el precio." · "Elige una categoría." |
| Tipos | Precio "abc" → "El precio debe ser un número, por ejemplo 3.50." · Existencias "2.5" → "…entero, sin decimales." · Nombre "Ana123" → "solo puede tener letras y espacios." |
| Rangos | Precio de $0 a $100 · Existencias de 0 a 9999 · Reponer de 1 a 1000 · Cantidad en el carrito de 1 a 20 y no más de lo disponible · Contraseña de 8+ caracteres con letra y número |
| Duplicados | Correo ya registrado → "Ya existe una cuenta con ese correo." · Producto con el mismo nombre (sin importar mayúsculas) → "Ya existe un producto de tienda llamado «Brownie»." · La base también lo impide con un índice `UNIQUE` |

Además, la base de datos tiene reglas `CHECK` (precio ≥ 0, existencias ≥ 0, cantidad > 0) como segunda barrera.

## Archivos que cambiaron en esta versión

| Archivo | Cambio |
|---|---|
| `dao/` (nuevo) | Interfaz `DAO` y `UsuarioDAO`, `CategoriaDAO`, `ProductoDAO`, `PedidoDAO`. Reemplaza a `repositorios.py`, que se borra |
| `modelos/categoria.py` (nuevo) | Clase `Categoria` |
| `modelos/excepciones.py` | `ErrorBaseDatos`, `RegistroDuplicado`, `RegistroEnUso`, `RegistroNoEncontrado` |
| `modelos/producto.py` | Rangos de precio y existencias; `incluye` y `presentacion` como propiedades que validan; mensajes más claros |
| `modelos/carrito.py`, `modelos/usuario.py`, `modelos/__init__.py` | Nombres y comentarios (DAO en vez de repositorio) |
| `servicios.py` | Usa los DAO; revisa duplicados; valida vacíos en login, registro y recuperación; nuevo `eliminar` |
| `base_datos.py` | Índice `UNIQUE` para nombres de producto |
| `datos_iniciales.py`, `app.py`, `contenedor.py` | Usan los DAO; `app.py` muestra una página clara si la base de datos falla |
| `rutas/admin.py` | Nueva página para eliminar productos (con confirmación) |
| `templates/admin/inventario.html`, `templates/admin/confirmar_eliminar.html` (nuevo) | Botón y página de "Eliminar" |
| `pruebas/test_cafeteria.py` | 45 pruebas (13 nuevas: DAO, CRUD, errores y validaciones) |
| `docs/` | Diagramas UML en 3 vistas, `CLASES.md`, `BASE_DE_DATOS.md`, `RAMAS.md`, este archivo y `GUIA_DEFENSA.md` |
