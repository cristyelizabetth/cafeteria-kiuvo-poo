# Guía para la presentación y la defensa

La presentación tiene tres partes: **demostración** (4–5 min), **diseño** (3 min) y **preguntas** (3–4 min). En las preguntas, el docente elige a quién preguntar y puede pedir **explicar o modificar código en vivo**, así que cada una debe dominar su parte y entender lo general.

---

## 1. Demostración (4–5 min): guion

**Antes de empezar:** borren `instancia/kiuvo.db` para arrancar con datos limpios, ejecuten `py app.py` y abran `http://127.0.0.1:5000`. Tengan dos ventanas: una normal (estudiante) y otra de incógnito (administrador).

| # | Qué hacer | Qué decir |
|---|---|---|
| 1 | Entrar como **estudiante** (`estudiante@kiuvo.com` / `Estudiante2026`) | "El estudiante solo ve los productos disponibles: activos y con existencias." |
| 2 | En **Almuerzos**, filtrar por "Ligero" y reservar 2 "Ensalada César" | "El filtro de categorías consulta la tabla `categorias` con un JOIN." |
| 3 | En **Tienda**, agregar 1 "Agua embotellada" y abrir el **Carrito** | "El carrito no deja pasar de las existencias reales." |
| 4 | **Pagar** con tarjeta simulada | "**Aquí se guarda en la base de datos:** `PedidoDAO.insertar` crea el pedido, descuenta el inventario y guarda el detalle en una sola transacción." |
| 5 | Abrir **Mis pedidos** | "**Y aquí se lee de la base de datos**: el pedido con sus líneas, leído de `pedidos` y `detalle_pedido`." |
| 6 | En la ventana del **administrador** (`admin@kiuvo.com` / `Kiuvo2026`), abrir **Inventario** | "La ensalada bajó de 4 a 2: los datos se guardaron de verdad." |
| 7 | **+ Producto de tienda**: crear "Horchata", $1.10, 15 unidades | "Create del CRUD." |
| 8 | Intentar crear otro "horchata", y otro con precio `-5` | "Validaciones: duplicados y rangos, con mensajes claros." |
| 9 | **Editar** la horchata (precio $1.25) y luego **Eliminar** | "Update y Delete del CRUD." |
| 10 | Intentar **Eliminar** "Agua embotellada" | "No deja, porque ya aparece en un pedido: la llave foránea lo impide y el DAO lo convierte en este mensaje. Por eso se oculta en vez de borrarse." |
| 11 | (Si sobra tiempo) Volver como estudiante y **cancelar** el pedido | "El inventario se devuelve en la misma transacción." |

## 2. Diseño (3 min)

Muestren las tres vistas del diagrama (`docs/diagrama_clases_1_modelo.png`, `_2_dao.png`, `_3_servicios.png`) y señalen:

1. **Herencia:** `Usuario` → `Estudiante` / `Administrador` y `Producto` → `Almuerzo` / `ProductoTienda` (triángulo blanco).
2. **Clases abstractas:** `Usuario`, `Producto` y `MetodoPago` (`«abstract»`, métodos en cursiva).
3. **Interfaz DAO y su implementación:** `DAO` (`«interface»`) y sus 4 implementaciones (triángulo con línea punteada).
4. **Capas:** rutas → servicios → DAO → base de datos. "Ningún servicio ni ruta escribe SQL."
5. **Multiplicidades:** un `Carrito` contiene `0..*` `ItemCarrito`; un `Pedido`, `1..*` `ItemPedido`.
6. **Visibilidad:** `+` público, `#` protegido, `-` privado (`__password_hash`).

---

## 3. Defensa individual: por persona

Para cada parte: qué archivos son tuyos, qué tienes que poder explicar, preguntas probables y cambios en vivo para practicar. **Practiquen los cambios en vivo antes de la defensa** y después deshagan el cambio con `git restore nombre_del_archivo`. Ojo: algunas pruebas automáticas pueden fallar después de un cambio, porque revisan el comportamiento original. Es normal.

### Persona 1: Modelos (`modelos/`)

**Explicar:** herencia de `Usuario` y `Producto`; propiedades que validan; polimorfismo (`puede_comprar`, `texto_boton`, `datos_extra`); composición `Carrito` ◆ `ItemCarrito` y `Pedido` ◆ `ItemPedido`; `EstadoPedido` como `Enum`; las excepciones propias.

**Preguntas probables:**
- *¿Por qué `Usuario` es abstracta?* → No existe un usuario "genérico": todo usuario es estudiante o administrador. `ABC` impide crear un `Usuario()` y `@abstractmethod` obliga a las hijas a implementar `puede_comprar()`, `pagina_principal()` y `descripcion_rol()`.
- *¿Qué hace `@property`?* → Convierte un método en un atributo controlado. Al escribir `producto.precio = -5` se ejecuta el setter, que valida y lanza `DatosInvalidos`.
- *¿Diferencia entre `_atributo` y `__atributo`?* → `_` es protegido por convención; `__` es privado: Python le cambia el nombre (*name mangling*) y no se puede leer desde fuera como `usuario.__password_hash`.
- *¿Dónde hay polimorfismo?* → La plantilla llama `p.texto_boton()` y un `Almuerzo` responde "Reservar" mientras un `ProductoTienda` responde "Agregar al carrito", sin ningún `if`.

**Cambios en vivo para practicar:**
1. *"Agrega la categoría Desayunos a los almuerzos."* → `modelos/producto.py`, clase `Almuerzo`: `CATEGORIAS = ("Plato del día", "Vegetariano", "Ligero", "Desayunos")`. Reinicien `py app.py`: aparece en el filtro y en el formulario, porque `CategoriaDAO.asegurar` la crea en la base al arrancar.
2. *"Que el precio máximo sea $50."* → `Producto.PRECIO_MAXIMO = 50.00`.
3. *"Que el carrito permita máximo 10 de cada producto."* → `modelos/carrito.py`: `MAXIMO_POR_PRODUCTO = 10`.
4. *"Agrega un método de pago con carnet."* → En `modelos/pago.py`, crear `class PagoConCarnet(MetodoPago)` con `CLAVE = "carnet"` y los métodos `nombre()`, `descripcion()` y `procesar(total)`. Luego agregar `PagoConCarnet()` a la lista de `disponibles()`. Aparece solo en la página de pago: eso es polimorfismo.

### Persona 2: Base de datos y DAO (`base_datos.py`, `dao/`, `datos_iniciales.py`)

**Explicar:** las 7 tablas y sus relaciones (`docs/diagrama_base_datos.png`); normalización; patrón DAO; CRUD; consultas parametrizadas; transacciones; conversión de errores en `DAO._conexion()`.

**Preguntas probables:**
- *¿Qué es un DAO y para qué sirve?* → Un objeto que se encarga solo del acceso a datos. Separa el SQL de la lógica y de la interfaz. Si cambiamos de base de datos, solo cambian los DAO.
- *¿Por qué `DAO` es abstracta?* → Es la interfaz: define el contrato (`insertar`, `buscar_por_id`, `listar`, `actualizar`, `eliminar`) y Python no deja crear un DAO que no lo cumpla.
- *¿Cómo evitan la inyección SQL?* → Con `?`: el valor se pasa aparte y SQLite nunca lo ejecuta como código.
- *¿Qué es una transacción? Muestra una.* → `PedidoDAO.insertar`: crea el pedido, descuenta cada producto y guarda el detalle. Si algún producto no alcanza, se lanza `InventarioInsuficiente` y se hace rollback de todo.
- *¿Qué pasa si se intenta borrar un producto vendido?* → La llave foránea de `detalle_pedido` lo impide, SQLite lanza `IntegrityError` y `DAO._conexion()` lo convierte en `RegistroEnUso` con un mensaje claro.

**Cambios en vivo para practicar:**
1. *"Agrega un método que liste los productos agotados."* → En `dao/producto_dao.py`, dentro de `ProductoDAO`:
   ```python
   def listar_agotados(self):
       with self._conexion() as con:
           filas = con.execute(self._SELECT + " WHERE p.existencias = 0 ORDER BY p.nombre").fetchall()
       return [self._a_objeto(f) for f in filas]
   ```
2. *"Cambia el mensaje cuando un producto está repetido."* → `ProductoDAO.MENSAJE_DUPLICADO`.
3. *"Agrega un producto de ejemplo."* → En `datos_iniciales.py`, agregar una línea a `PRODUCTOS_TIENDA`. Para verlo, borren `instancia/kiuvo.db` y reinicien, porque los ejemplos solo se cargan si la tabla está vacía.

### Persona 3: Seguridad y servicios (`seguridad.py`, `servicios.py`, `config.py`)

**Explicar:** los tres servicios y por qué existen (la lógica no va en las rutas ni en los DAO); hash de contraseñas; bloqueo por intentos; CSRF; validaciones de registro, login e inventario; revisión de duplicados.

**Preguntas probables:**
- *¿Cómo se guardan las contraseñas?* → Como hash con `werkzeug.security.generate_password_hash`. No se pueden revertir. Al iniciar sesión se compara con `check_password_hash`.
- *¿Por qué el login dice lo mismo si el correo no existe o la contraseña está mal?* → Para que nadie pueda averiguar qué correos están registrados.
- *¿Qué es CSRF?* → Que otro sitio envíe un formulario a nuestro sitio en tu nombre. Cada formulario lleva un token secreto de la sesión, y `ProtectorCSRF` rechaza los POST sin él.
- *¿Dónde se valida que no haya productos repetidos?* → `ServicioInventario._revisar_duplicado()` pregunta a `ProductoDAO.existe_nombre()`. Además, la base tiene un índice `UNIQUE` por si acaso.

**Cambios en vivo para practicar:**
1. *"Que la contraseña pida mínimo 9 caracteres."* → `seguridad.py`: `LONGITUD_MINIMA = 9`. Si lo suben a 10 o más, cambien también la contraseña del admin en `datos_iniciales.py` (`Kiuvo2026` tiene 9) o no arrancará con una base nueva.
2. *"Que bloquee después de 3 intentos."* → `config.py`: `INTENTOS_LOGIN = 3`.
3. *"Que la contraseña exija una mayúscula."* → En `ValidadorContrasena.errores()`, agregar:
   ```python
   if not re.search(r"[A-ZÁÉÍÓÚÑ]", contrasena):
       errores.append("Debe incluir al menos una mayúscula.")
   ```

### Persona 4: Rutas y aplicación (`app.py`, `contenedor.py`, `sesion.py`, `rutas/`, `pruebas/`)

**Explicar:** cómo `app.py` crea los DAO y servicios y los une; los Blueprints (`auth`, `estudiante`, `admin`); los decoradores de permisos; el carrito en la sesión; las páginas de error; las pruebas automáticas.

**Preguntas probables:**
- *¿Cómo impiden que el admin compre?* → El decorador `solo_compradores` (en `sesion.py`) pregunta `usuario.puede_comprar()`. El admin responde `False` (polimorfismo) y recibe un 403.
- *¿Por qué las rutas no tienen SQL?* → Solo reciben la petición, llaman a un servicio y muestran una plantilla. La lógica está en los servicios y los datos en los DAO.
- *¿Qué pasa si la base de datos falla?* → El DAO lanza `ErrorBaseDatos` y `app.py` tiene un `errorhandler` que muestra "Base de datos no disponible" en vez de un error técnico.
- *¿Cómo prueban que todo funciona?* → `py -m unittest discover pruebas`: 45 pruebas que simulan un navegador.

**Cambios en vivo para practicar:**
1. *"Que la sesión dure 1 hora."* → `config.py`: `PERMANENT_SESSION_LIFETIME = timedelta(hours=1)`.
2. *"Muestra en el panel cuántos pedidos cancelados hay."* → En `rutas/admin.py`, función `panel()`, agregar al diccionario `"cancelados": c.pedidos.contar("cancelado")`, y en `templates/admin/panel.html` copiar un `indicador` con `{{ resumen.cancelados }}`.
3. *"Ejecuta las pruebas."* → `py -m unittest discover pruebas -v`.

### Persona 5: Diseño, plantillas y documentación (`templates/`, `static/`, `docs/`)

**Explicar:** el diseño responsive (*mobile first*); la plantilla base y la herencia de plantillas de Jinja (`{% extends %}`); cómo las plantillas usan los métodos polimórficos; los diagramas UML y su notación.

**Preguntas probables:**
- *¿Cómo hicieron el sitio responsive?* → Estilos pensados primero para celular, y luego `@media (min-width: 640px)` y `(min-width: 960px)` para pantallas grandes. En celular, el menú se despliega y las tablas se vuelven tarjetas.
- *¿Coincide el diagrama con el código?* → Sí: cada clase, atributo y método del diagrama existe en el código. Por ejemplo, `ProductoDAO.existe_nombre` está en `dao/producto_dao.py`.
- *¿Qué significan `+`, `#` y `-`?* → Público, protegido (`_` en Python) y privado (`__` en Python).
- *¿Qué significa `1..*` entre `Pedido` e `ItemPedido`?* → Un pedido tiene al menos un ítem y puede tener muchos. Y es composición (rombo negro): los ítems no existen sin su pedido.

**Cambios en vivo para practicar:**
1. *"Cambia el color principal del sitio."* → `static/css/estilos.css`: `--acento` en `:root`.
2. *"Cambia el texto de la portada."* → `templates/inicio.html`.
3. *"Agrega un campo al diagrama."* → Editar el `.mmd` correspondiente en `docs/` y volver a generar la imagen en https://mermaid.live (pegar el texto → **Actions** → **PNG**).

---

## Preguntas que pueden caerle a cualquiera

- **¿Qué es la POO y dónde la usan?** Organizar el programa en clases que juntan datos y comportamiento. Usamos encapsulamiento, herencia, polimorfismo, abstracción y composición (`docs/CLASES.md`, tabla final).
- **¿Cuál es el flujo de una compra?** Ruta `/pagar` → `ServicioPedidos.confirmar_compra` → `Pedido.desde_carrito` → `PedidoDAO.insertar` (transacción) → `metodo.procesar()` → mensaje.
- **¿Por qué SQLite?** Viene con Python, no necesita servidor y es un solo archivo. Con los DAO se podría cambiar a MySQL sin tocar la lógica.
- **¿Qué cambiaron después del avance 1?** Base de datos conectada y normalizada (7 tablas), validaciones en tres niveles, capa DAO con CRUD completo, manejo de excepciones y diagrama UML actualizado (`docs/CAMBIOS_RUBRICA.md`).
