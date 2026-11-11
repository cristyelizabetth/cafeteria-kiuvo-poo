# Pruebas de seguridad: qué atacamos y qué pasó

Cada ataque se hizo contra el sitio funcionando y quedó automatizado como prueba: los ataques 1 a 7 y el 11 están en `tests/test_seguridad.py`; el 8, 9, 10 y 12, en `tests/test_cafeteria.py`. Se repiten todos con `python -m unittest -v`.

| # | Ataque | Qué intentamos | Qué pasó | Por qué |
|---|---|---|---|---|
| 1 | **Inyección SQL en el login** | Escribir `' OR '1'='1` en el correo y en la contraseña, y `admin@kiuvo.com' --` para "comentar" la revisión de contraseña | No entra. Sale "Correo o contraseña incorrectos" y cuenta como intento fallido | Todas las consultas usan parámetros `?`: el texto se busca tal cual como un correo y nunca se ejecuta como SQL |
| 2 | **Inyección SQL al guardar** | Crear un producto llamado `Té'); DROP TABLE productos; --` | Se guarda como un nombre normal y la tabla sigue con todos sus productos | Igual que el 1: el valor va como parámetro, no pegado al SQL |
| 3 | **Inyección SQL en la URL** | Abrir `/tienda?categoria=' OR '1'='1` | La página carga normal y el filtro se ignora | Solo se aceptan categorías de la lista oficial; además la consulta es parametrizada |
| 4 | **Datos vacíos, negativos o con formato malo** | Producto sin nombre, precio `-3` o `tres`, existencias `-4`, `dos` o `2.5`; reponer `-10`; carrito con `-5`; correo `ana-arroba-correo` | Se rechazan con un mensaje claro y **no llega nada a la base de datos** | Las propiedades de los modelos y los servicios validan antes del DAO. Si alguien se saltara Python, las reglas `CHECK` de SQLite lo frenan |
| 5 | **Llave foránea inválida** | Guardar un pedido de un estudiante que no existe o un producto con una categoría que no existe | Se rechaza (`ReferenciaInvalida`) y no queda nada a medias | `PRAGMA foreign_keys = ON` en cada conexión y transacciones (`with ... conexion()`) |
| 6 | **Robar contraseñas de la base** | Abrir la tabla `usuarios` | Solo se ven *hashes* (`scrypt:...`); no aparecen la contraseña ni la respuesta secreta | `generate_password_hash` de werkzeug |
| 7 | **Provocar un error interno** | Forzar una falla del servidor y abrir páginas que no existen | Sale "Algo salió mal" o "Página no encontrada". **Nunca** un *traceback*, nombres de archivos ni el error técnico | `DEBUG` apagado y páginas de error propias (`errorhandler` 404, 500 y de base de datos) |
| 8 | **Fuerza bruta** | Probar contraseñas muchas veces | Al 5.º intento fallido la cuenta se bloquea 5 minutos | `LimitadorIntentos` |
| 9 | **Formulario desde otro sitio (CSRF)** | Enviar un formulario sin el token secreto | Se rechaza (400) | `ProtectorCSRF` en todos los formularios |
| 10 | **Entrar donde no toca** | Un estudiante abre `/admin/`; el admin intenta comprar | 403 "Acceso denegado" | Decoradores por rol en `sesion.py` |
| 11 | **Scripts en los datos (XSS)** | Nombre de producto con `<script>` | Se muestra como texto, no se ejecuta | Jinja escapa todo y hay encabezado CSP |
| 12 | **Archivo disfrazado de foto** | Subir un texto renombrado a `.jpg`, una imagen de más de 2 MB o pedir `/imagenes/../app.py` | Se rechaza o da 404 | `GestorImagenes` revisa los primeros bytes, el tamaño y usa nombres al azar |

**Conclusión:** ninguno de los ataques logró entrar, borrar datos ni mostrar información interna. Lo que encontramos al probar y corregimos fue: existencias con decimales (`2.5`) que se redondeaban sin avisar y que el modelo `ItemPedido` aceptaba cantidades en cero o negativas. Ahora las dos se rechazan antes de llegar a la base de datos, y hay pruebas que lo revisan.
