# Cafetería Kiuvo

Sitio web de la cafetería universitaria. Los estudiantes reservan almuerzos y compran productos de la tienda; el administrador gestiona los almuerzos y el inventario.

Hecho con **Python + Flask** y **SQLite**, con enfoque de **Programación Orientada a Objetos**.

---

## Cómo ejecutarlo

Necesitas Python 3.10 o más reciente.

```bash
# 1. (Opcional, recomendado) crear un entorno virtual
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Mac / Linux:  source .venv/bin/activate

# 2. Instalar Flask
pip install -r requirements.txt

# 3. Ejecutar
python app.py
```

Abre **http://127.0.0.1:5000** en el navegador.

La primera vez se crea sola la carpeta `instancia/` con la base de datos (`kiuvo.db`) y la clave secreta. Esa carpeta **no se sube a GitHub** (está en `.gitignore`). Si quieres empezar con la base de datos limpia, borra `instancia/kiuvo.db` y vuelve a ejecutar.

### Cuentas de prueba

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@kiuvo.com` | `Kiuvo2026` |
| Estudiante | `estudiante@kiuvo.com` | `Estudiante2026` |

Respuesta de seguridad de ambas cuentas (para probar "¿Olvidaste tu contraseña?"): `pupusas`.

### Pruebas automáticas

```bash
python -m unittest discover pruebas -v
```

Son 45 pruebas que revisan las clases, la capa DAO (CRUD y errores), la base de datos normalizada, las validaciones, la seguridad y todos los flujos (registro, login, recuperar contraseña, comprar, cancelar, funciones del administrador).

---

## Qué puede hacer cada usuario

**Estudiante**
- Crear cuenta (con pregunta de seguridad) e iniciar sesión.
- Ver **solo los productos disponibles**: activos y con existencias.
- Filtrar almuerzos y productos de tienda por categoría.
- Agregar al carrito, cambiar cantidades y quitar productos.
- Pagar (simulado): en caja al retirar o con tarjeta simulada.
- Ver sus pedidos y **cancelar** los que están pendientes. Lo cancelado vuelve al inventario.

**Administrador**
- Panel con resumen: productos, agotados, existencias bajas y pedidos pendientes.
- Ver **todo el inventario**, incluidos los productos agotados y ocultos.
- Crear, editar y **eliminar** almuerzos y productos de tienda (no deja eliminar los que ya se vendieron, para no perder el historial: esos se ocultan).
- Ocultar o mostrar un producto a los estudiantes.
- Reponer existencias.
- Ver los pedidos de los estudiantes.
- **No puede** comprar ni reservar.

---

## Cómo se cumplen las recomendaciones del profesor

| # | Recomendación | Dónde está |
|---|---|---|
| 1 | Sitio responsive | `static/css/estilos.css`: diseño *mobile first*, menú desplegable en celular, tablas que se vuelven tarjetas, botones y campos de 44 px para tocar con el dedo. |
| 2 | Encriptar contraseñas | `modelos/usuario.py`: se guardan como **hash** con `werkzeug` (`generate_password_hash`). La respuesta de seguridad también. Nunca se guarda el texto original. |
| 3 | Darle seguridad | Ver la sección siguiente. |
| 4 | Hacer un diagrama | `docs/diagrama_clases.png` (clases) y `docs/diagrama_base_datos.png` (tablas). |
| 5 | Conocer las clases | `docs/CLASES.md` explica cada clase y dónde se usa cada concepto de POO. |
| 6 | "Olvidé mi contraseña" | Enlace en el login → `/recuperar`. Funciona con una pregunta de seguridad elegida al registrarse. |

### Medidas de seguridad

| Medida | Qué evita | Dónde |
|---|---|---|
| Contraseñas con hash | Que se lean si alguien roba la base de datos | `Usuario.crear`, `cambiar_contrasena` |
| Reglas de contraseña (8+ caracteres, letra y número) | Contraseñas fáciles de adivinar | `ValidadorContrasena` |
| Bloqueo de 5 min tras 5 intentos fallidos | Que prueben contraseñas a la fuerza | `LimitadorIntentos` |
| Mismo mensaje si el correo no existe o la contraseña está mal | Averiguar qué correos están registrados | `ServicioAutenticacion.iniciar_sesion` |
| Token CSRF en todos los formularios | Que otro sitio envíe formularios en tu nombre | `ProtectorCSRF` + `app.py` |
| Consultas SQL con parámetros `?` | Inyección SQL | Carpeta `dao/` |
| Control de acceso por rol | Que un estudiante entre al panel o que el admin compre | Decoradores en `sesion.py` |
| Clave secreta fuera del código | Que alguien falsifique una sesión | `config.py` |
| Debug apagado por defecto | Mostrar código y errores internos | `config.py` |
| Cookie de sesión `HttpOnly`, `SameSite`, expira en 2 h | Robo de la sesión | `config.py` |
| Encabezados de seguridad (CSP, X-Frame-Options…) | Clickjacking y scripts inyectados | `app.py` |
| Escapado automático de Jinja | Inyección de HTML (XSS) | Plantillas |
| Redirecciones solo internas | Que te manden a un sitio falso | `rutas/auth.py`, `rutas/admin.py` |

### Variables de entorno (opcionales)

| Variable | Para qué |
|---|---|
| `KIUVO_SECRET_KEY` | Clave secreta propia. Si no existe, se genera una y se guarda en `instancia/`. |
| `KIUVO_DEBUG=1` | Encender el modo debug mientras desarrollan. |
| `KIUVO_COOKIE_SEGURA=1` | Enviar la cookie solo por HTTPS (activar si lo publican en internet). |
| `KIUVO_ADMIN_PASSWORD` | Contraseña del admin que se crea la primera vez. |
| `KIUVO_BASE_DATOS` | Ruta de otro archivo de base de datos. |

---

## Estructura del proyecto

```
cafeteria-kiuvo/
├── app.py                  ← crea la aplicación y une todas las piezas
├── config.py               ← configuración (clave secreta, cookies, debug)
├── contenedor.py           ← guarda los DAO y servicios en un solo objeto
├── sesion.py               ← usuario actual, permisos por rol, carrito en sesión
├── seguridad.py            ← ValidadorContrasena, LimitadorIntentos, ProtectorCSRF
├── servicios.py            ← reglas del negocio (autenticación, pedidos, inventario)
├── base_datos.py           ← clase BaseDatos: conexión, tablas de SQLite y actualización de bases viejas
├── datos_iniciales.py      ← cuentas y productos de ejemplo
├── dao/                    ← capa DAO: la única que escribe SQL
│   ├── base.py             ← DAO: interfaz (clase abstracta) con el CRUD y el manejo de errores
│   ├── usuario_dao.py      ← UsuarioDAO
│   ├── categoria_dao.py    ← CategoriaDAO
│   ├── producto_dao.py     ← ProductoDAO
│   └── pedido_dao.py       ← PedidoDAO
├── modelos/                ← las clases del dominio
│   ├── usuario.py          ← Usuario → Estudiante, Administrador
│   ├── producto.py         ← Producto → Almuerzo, ProductoTienda
│   ├── categoria.py        ← Categoria
│   ├── carrito.py          ← Carrito, ItemCarrito
│   ├── pedido.py           ← Pedido, ItemPedido, EstadoPedido
│   ├── pago.py             ← MetodoPago → PagoEnCaja, PagoTarjetaSimulado
│   └── excepciones.py      ← ErrorCafeteria y sus hijas
├── rutas/                  ← páginas, separadas por tipo de usuario
│   ├── auth.py             ← inicio, registro, login, recuperar contraseña
│   ├── estudiante.py       ← catálogos, carrito, pago, mis pedidos
│   └── admin.py            ← panel, inventario, productos, pedidos
├── templates/              ← HTML (Jinja)
├── static/css/estilos.css  ← estilos responsive
├── pruebas/                ← pruebas automáticas
└── docs/                   ← diagramas y explicaciones
```

**Cómo viaja una petición:** el navegador pide una página → una **ruta** (`rutas/`) recibe la petición → llama a un **servicio** (`servicios.py`) → el servicio usa los **modelos** (`modelos/`) y la **capa DAO** (`dao/`) → el DAO habla con **SQLite** → la ruta muestra el resultado con una **plantilla** (`templates/`).

Más detalle:
- `docs/CLASES.md`: cada clase y los conceptos de POO.
- `docs/BASE_DE_DATOS.md`: cómo funciona la base de datos.
- `docs/CAMBIOS_NORMALIZACION.md`: qué cambió al normalizar la base de datos.
- `docs/CAMBIOS_RUBRICA.md`: cómo cumple cada criterio de la rúbrica final.
- `docs/GUIA_DEFENSA.md`: guion de la demo y preparación de la defensa individual.
- `docs/RAMAS.md`: cómo subir el proyecto entre las cinco con ramas y Pull Requests.
