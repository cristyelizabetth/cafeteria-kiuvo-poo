# Las clases del proyecto

El diagrama de clases está en tres vistas, para que se pueda leer:
- `diagrama_clases_1_modelo.png`: usuarios, productos, carrito, pedidos y pagos.
- `diagrama_clases_2_dao.png`: la interfaz DAO y sus implementaciones.
- `diagrama_clases_3_servicios.png`: servicios, seguridad y excepciones.

`diagrama_clases.png` es el diagrama completo en una sola imagen (los `.svg` permiten hacer zoom sin que se pixele).

**Notación UML:** `+` público · `#` protegido (atributo `_nombre` en Python) · `-` privado (atributo `__nombre`) · subrayado o `$` = estático · cursiva o `*` = abstracto · triángulo = herencia · triángulo con línea punteada = implementa una interfaz · rombo negro = composición · rombo blanco = agregación · números en las líneas = multiplicidad (`1`, `0..*`, `1..*`).

Las clases están en tres grupos:

1. **Modelos** (`modelos/`): lo que el sistema *es*. Usuarios, productos, carrito, pedidos y pagos.
2. **Acceso a datos, capa DAO** (`base_datos.py`, carpeta `dao/`): guardar y leer los objetos en SQLite.
3. **Servicios y seguridad** (`servicios.py`, `seguridad.py`): reglas que usan varias clases a la vez.

---

## 1. Modelos

### `Usuario` (abstracta) → `Estudiante`, `Administrador`
**Archivo:** `modelos/usuario.py`

- `Usuario` es **abstracta** (hereda de `ABC`): no se puede crear un "usuario" genérico, solo un `Estudiante` o un `Administrador`.
- Guarda nombre, correo, pregunta de seguridad y los **hash** de la contraseña y de la respuesta.
- `__password_hash` y `__respuesta_hash` son **privados**: desde fuera de la clase no se pueden leer ni cambiar directamente. Para cambiar la contraseña hay que llamar a `cambiar_contrasena()`, que primero revisa las reglas de seguridad.
- `Usuario.crear(...)` recibe la contraseña en texto, la valida, la convierte en hash y devuelve el objeto.
- `Usuario.construir(rol, ...)` es una **fábrica**: según el rol que viene de la base de datos devuelve un `Estudiante` o un `Administrador`.

| Método | `Estudiante` | `Administrador` |
|---|---|---|
| `puede_comprar()` | `True` | `False` |
| `pagina_principal()` | Catálogo de almuerzos | Panel de administración |
| `descripcion_rol()` | "Estudiante" | "Administrador" |
| `puede_gestionar_inventario()` | `False` (heredado) | `True` |

**¿Por qué herencia aquí?** Estudiante y administrador comparten casi todo (nombre, correo, contraseña, recuperación), pero se comportan distinto en lo que pueden hacer. La parte común se escribe una sola vez en `Usuario` y cada hija cambia solo lo suyo. Las rutas preguntan `usuario.puede_comprar()` en vez de `if rol == "admin"`, así que agregar un rol nuevo (por ejemplo, "Cajero") sería crear otra clase hija sin tocar las rutas.

Las rutas preguntan `usuario.puede_comprar()` sin revisar de qué clase es: cada objeto responde a su manera. Eso es **polimorfismo**.

### `Producto` (abstracta) → `Almuerzo`, `ProductoTienda`
**Archivo:** `modelos/producto.py`

- Atributos comunes: nombre, descripción, categoría, precio, existencias y si está activo (visible).
- Los atributos son **propiedades con validación** (getters y setters). Así ningún formulario puede meter datos imposibles:

| Propiedad | Vacío | Tipo | Rango |
|---|---|---|---|
| `nombre` | "El nombre no puede estar vacío." | texto | máx. 80 caracteres |
| `precio` | "Escribe el precio." | número ("abc" → "debe ser un número") | de $0.00 a $100.00 |
| `existencias` | "Escribe las existencias." | entero ("2.5" → "sin decimales") | de 0 a 9999 |
| `categoria` | "Elige una categoría." | debe ser de su tipo | — |
| `incluye` / `presentacion` | se permite | texto | máx. 120 caracteres |
- `descontar(cantidad)` lanza `InventarioInsuficiente` si no alcanza.
- `esta_disponible()` → activo y con existencias. Es lo que decide qué ve el estudiante.
- `estado_inventario()` → "Disponible", "Bajo", "Agotado" u "Oculto", para la tabla del admin.

| Método o atributo | `Almuerzo` | `ProductoTienda` |
|---|---|---|
| Atributo propio | `incluye` (acompañamientos) | `presentacion` (botella 600 ml…) |
| `CATEGORIAS` | Plato del día, Vegetariano, Ligero | Bebidas, Snacks, Postres |
| `texto_boton()` | "Reservar" | "Agregar al carrito" |
| `etiqueta_existencias()` | "Quedan 12 porciones" | "12 disponible(s)" |
| `TABLA_DETALLE` (tabla con sus datos propios) | `almuerzos` | `productos_tienda` |
| `datos_extra()` | `{"incluye": ...}` | `{"presentacion": ...}` |
| `UMBRAL_EXISTENCIAS_BAJAS` | 5 | 10 |

La plantilla `_tarjeta_producto.html` es la misma para los dos y solo llama `p.texto_boton()`: el texto correcto sale del objeto.

### `Carrito` y `ItemCarrito`
**Archivo:** `modelos/carrito.py`

- Un `Carrito` **contiene** varios `ItemCarrito` (**composición**). Cada item tiene un producto y una cantidad, y calcula su `subtotal`.
- `agregar()` y `cambiar_cantidad()` no permiten pasar las existencias ni agregar productos no disponibles.
- En la sesión del navegador solo se guarda `{id: cantidad}` (`a_dict()`). En cada página se reconstruye con datos actuales de la base (`desde_dict()`). Si mientras tanto un producto se agotó o subió de precio, el carrito se corrige solo y avisa.

### `Pedido`, `ItemPedido` y `EstadoPedido`
**Archivo:** `modelos/pedido.py`

- Un `Pedido` **contiene** uno o más `ItemPedido` (composición).
- `Pedido.desde_carrito()` convierte el carrito en pedido.
- `ItemPedido` guarda una **copia** del nombre y del precio del momento de la compra. Si el admin cambia el precio mañana, los pedidos viejos no cambian.
- `EstadoPedido` es una **enumeración** (`Enum`): solo puede valer `PENDIENTE` o `CANCELADO`.
- `cancelar()` revisa con `puede_cancelarse()` y lanza `PedidoNoCancelable` si ya estaba cancelado.

### `MetodoPago` (abstracta) → `PagoEnCaja`, `PagoTarjetaSimulado`
**Archivo:** `modelos/pago.py`

- Cada método implementa `nombre()`, `descripcion()` y `procesar(total)`.
- `ServicioPedidos` llama `metodo.procesar(total)` sin saber cuál es; cada uno devuelve su propio mensaje (**polimorfismo**).
- Para agregar otro método (por ejemplo, "Pago con carnet") basta con crear otra clase hija y agregarla en `disponibles()`.

### Excepciones propias
**Archivo:** `modelos/excepciones.py`

Todas heredan de `ErrorCafeteria`: `ErrorBaseDatos` (con sus hijas `RegistroDuplicado`, `RegistroEnUso` y `RegistroNoEncontrado`, que lanza la capa DAO), `DatosInvalidos`, `InventarioInsuficiente`, `ProductoNoDisponible`, `PedidoNoCancelable`, `CredencialesInvalidas`, `CuentaBloqueada`, `ContrasenaInvalida` y `CorreoYaRegistrado`. Las rutas solo atrapan `except ErrorCafeteria` y muestran el mensaje, sin importar cuál fue.

---

## 2. Acceso a datos

### `BaseDatos`
**Archivo:** `base_datos.py`

Abre la conexión con SQLite, crea las tablas y ofrece `conexion()`, que agrupa operaciones en una **transacción**. No sabe nada de estudiantes ni de productos.

### Capa DAO: `DAO` (interfaz) → `UsuarioDAO`, `CategoriaDAO`, `ProductoDAO`, `PedidoDAO`
**Carpeta:** `dao/`

**DAO** significa *Data Access Object* (objeto de acceso a datos). Es la **única** capa que escribe SQL. Las rutas (interfaz) y los servicios (lógica) le piden los datos a un DAO y nunca hablan directamente con la base:

```
Rutas (interfaz)  →  Servicios (lógica)  →  DAO (datos)  →  SQLite
```

**`DAO` (`dao/base.py`)** es una clase abstracta que funciona como **interfaz**: define las operaciones CRUD que todo DAO debe tener, y Python no deja crear un DAO que no las implemente todas.

| Operación | Método abstracto | SQL |
|---|---|---|
| **C**reate (crear) | `insertar(entidad)` | `INSERT` |
| **R**ead (leer) | `buscar_por_id(id)`, `listar(**filtros)` | `SELECT` |
| **U**pdate (actualizar) | `actualizar(entidad)` | `UPDATE` |
| **D**elete (eliminar) | `eliminar(id)` | `DELETE` |

Además, la clase `DAO` trae métodos que heredan todos:
- `guardar(entidad)`: inserta si es nueva o actualiza si ya tiene id.
- `_conexion()`: abre una **transacción** (todo o nada) y **convierte los errores de SQLite** en excepciones propias con mensajes claros:
  - un dato repetido (`UNIQUE`) → `RegistroDuplicado` ("Ya existe un producto con ese nombre.");
  - borrar algo que otros usan (`FOREIGN KEY`) → `RegistroEnUso` ("Este producto ya aparece en pedidos… Puedes ocultarlo.");
  - cualquier otro fallo → `ErrorBaseDatos` ("No se pudo acceder a la base de datos.").
- `_confirmar_afectadas()`: avisa con `RegistroNoEncontrado` si un `UPDATE` o `DELETE` no encontró la fila.

| DAO | Tablas | Métodos propios además del CRUD |
|---|---|---|
| `UsuarioDAO` | `usuarios` | `buscar_por_correo`, `existe_correo`, `contar` |
| `CategoriaDAO` | `categorias` | `asegurar` (crea las categorías oficiales), `buscar_id` |
| `ProductoDAO` | `productos`, `almuerzos`, `productos_tienda` | `existe_nombre`, `contar`, `_guardar_detalle` |
| `PedidoDAO` | `pedidos`, `detalle_pedido` | `cancelar` (cambia el estado y devuelve el inventario), `contar` |

`ProductoDAO` reparte cada producto en dos tablas: lo común va a `productos` y lo propio va a la tabla que indica la clase (`TABLA_DETALLE`), con los datos de `datos_extra()`. El DAO no pregunta "¿es almuerzo o tienda?": cada objeto dice dónde van sus datos (**polimorfismo**).

Todos los DAO usan **consultas parametrizadas** (`?`) y **reciben** un objeto `BaseDatos` en su constructor (**agregación**).

**¿Por qué una interfaz?** Si mañana cambian SQLite por MySQL, solo se escribe otra implementación de cada DAO con los mismos métodos. Los servicios y las rutas no cambian, porque solo conocen el "contrato" de `DAO`.

### `Categoria`
**Archivo:** `modelos/categoria.py`

Una categoría ("Bebidas", "Vegetariano"…) con su tipo (`almuerzo` o `tienda`). Sus propiedades validan que el nombre no esté vacío ni sea muy largo y que el tipo sea válido.

---

## 3. Servicios y seguridad

| Clase | Archivo | Qué hace |
|---|---|---|
| `ServicioAutenticacion` | `servicios.py` | Registro de estudiantes, inicio de sesión con límite de intentos y recuperación de contraseña. |
| `ServicioPedidos` | `servicios.py` | Confirmar compras (crea el pedido, descuenta inventario y procesa el pago) y cancelar pedidos. |
| `ServicioInventario` | `servicios.py` | CRUD de productos del admin: crear, ver, editar, ocultar o mostrar, reponer y eliminar. Revisa que no se repitan nombres. |
| `ValidadorContrasena` | `seguridad.py` | Reglas de contraseña. Sus métodos son de clase (`@classmethod`): se usa sin crear objetos. |
| `LimitadorIntentos` | `seguridad.py` | Cuenta los intentos fallidos y bloquea 5 minutos al llegar a 5. |
| `ProtectorCSRF` | `seguridad.py` | Genera y revisa el token secreto de los formularios. |
| `Contenedor` | `contenedor.py` | Guarda en un solo objeto los DAO y servicios para que las rutas los usen. |

---

## Resumen: dónde se ve cada concepto de POO

| Concepto | Ejemplo en el proyecto |
|---|---|
| **Clase y objeto** | `Almuerzo` es la clase; "Pollo guisado" es un objeto de esa clase. |
| **Encapsulamiento** | `Usuario.__password_hash` es privado; el precio de `Producto` solo cambia por su propiedad, que valida. |
| **Herencia** | `Estudiante` y `Administrador` heredan de `Usuario`; `Almuerzo` y `ProductoTienda` de `Producto`; las excepciones de `ErrorCafeteria`. |
| **Polimorfismo** | `puede_comprar()`, `pagina_principal()`, `texto_boton()`, `etiqueta_existencias()`, `datos_extra()`, `procesar()`; y los cuatro DAO con los mismos métodos CRUD. |
| **Abstracción e interfaz** | `Usuario`, `Producto` y `MetodoPago` son clases abstractas con métodos `@abstractmethod`. `DAO` es la interfaz de la capa de datos. |
| **Composición** | `Carrito` contiene `ItemCarrito`; `Pedido` contiene `ItemPedido`. |
| **Agregación** | Los DAO reciben un `BaseDatos`; los servicios reciben DAO. |
| **Métodos de clase / estáticos** | `Usuario.crear()`, `Producto.construir()`, `ValidadorContrasena.validar()`. |
| **Enumeración** | `EstadoPedido`. |
| **Excepciones propias** | `InventarioInsuficiente`, `CuentaBloqueada`, etc. |
