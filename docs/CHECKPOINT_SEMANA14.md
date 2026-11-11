# Checkpoint semana 14: base de datos, pruebas y seguridad

20 puntos en 15 minutos. **No llevan diapositivas**: todo se muestra con el código y el programa funcionando. Al minuto 15 se corta, y lo que no se mostró no cuenta.

## Dónde está cada punto de la rúbrica

| Aspecto | Pts | Qué piden | Dónde lo mostramos |
|---|---|---|---|
| Modelo y esquema | 2 | Tablas basadas en el UML, con PK y FK | `docs/esquema.sql`, `docs/diagrama_base_datos.png` y `base_datos.py` (`ESQUEMA`) |
| DAO y capas | 3 | Interfaz DAO + CRUD completo; devuelve objetos; nada de SQL fuera del DAO | `dao/base.py` (interfaz `DAO`) y `dao/producto_dao.py`. La prueba `test_todas_las_consultas_estan_en_el_dao_y_usan_parametros` revisa que no haya SQL fuera |
| Persistencia y transacciones | 3 | Los datos siguen al reabrir; `with conexion:` al escribir; `PRAGMA foreign_keys = ON` | Demo de cerrar y reabrir; `BaseDatos.conexion()` (commit o rollback) y `BaseDatos._nueva_conexion()` (PRAGMA) |
| Cobertura | 3 | CRUD de cada DAO y 2+ reglas de negocio, con `:memory:` | `tests/test_dao.py` (`PruebasCRUD`: un test por DAO) y `tests/test_reglas_negocio.py` (6 reglas) |
| Casos borde | 2 | Id inexistente, datos inválidos, FK inválida | `tests/test_dao.py`, clase `PruebasCasosBorde` |
| Ejecución en vivo | 1 | Todas pasan en la presentación | `py -m unittest` → `Ran 87 tests ... OK` |
| Inyección SQL | 3 | Todo parametrizado; `' OR '1'='1` no afecta | Demo en el login + `SEGURIDAD.md` |
| Validación de entrada | 2 | Rechaza vacíos, negativos y formatos malos antes de la BD | Demo en el formulario de producto |
| Contraseñas y errores | 1 | Hash y nunca un *traceback* | Columna `password_hash` + página "Algo salió mal" |

## Antes de entrar (5 minutos antes)

1. En Git Bash, en la carpeta del proyecto: `git checkout main` y `git pull`.
2. Abre VS Code en esa carpeta con estas pestañas listas: `docs/esquema.sql`, `dao/base.py`, `dao/producto_dao.py`, `tests/test_dao.py` y `SEGURIDAD.md`.
3. Abre DB Browser for SQLite con `instancia/kiuvo.db` (opcional, pero se ve muy bien).
4. Ten **dos** terminales: una para el servidor (`py app.py`) y otra para las pruebas.
5. Ejecuta `py -m unittest` una vez antes de entrar, para confirmar que todo pasa.

## Guion de 15 minutos

### Min 0–3 · Esquema de la BD y una clase DAO
- Abrir `docs/esquema.sql` (o el diagrama). *"Son 7 tablas que salen de nuestro UML: `usuarios` es la clase `Usuario`, `productos` es `Producto`, y `almuerzos` y `productos_tienda` son sus clases hijas. Cada tabla tiene su llave primaria `id`, y las llaves foráneas unen pedidos con usuarios, detalle con pedidos y productos, y productos con categorías."*
- Abrir `dao/base.py`. *"Esta es la interfaz DAO: una clase abstracta con insertar, buscar_por_id, listar, actualizar y eliminar. Los cuatro DAO la implementan."*
- Abrir `dao/producto_dao.py` → `buscar_por_id` y `_a_objeto`. *"El DAO hace la consulta con `?` y convierte la fila en un objeto `Almuerzo` o `ProductoTienda`. Ningún otro archivo escribe SQL."*

### Min 3–6 · Crear, cerrar, reabrir
1. `py app.py` → entrar como admin → **+ Producto de tienda** → crear "Horchata" ($1.00, 10).
2. Volver a la terminal y presionar **Ctrl + C** (el servidor se apaga).
3. `py app.py` otra vez → Inventario → **"Horchata" sigue ahí**.
4. *"Se guardó en el archivo `instancia/kiuvo.db`. Cada escritura va dentro de `with self._conexion() as con:`: si todo sale bien hace commit, y si algo falla hace rollback. Y cada conexión activa `PRAGMA foreign_keys = ON`."* Mostrar `base_datos.py`, métodos `_nueva_conexion` y `conexion`.

### Min 6–9 · Pruebas unitarias
1. En la segunda terminal: `py -m unittest`. Tarda unos 40 segundos: mientras corre, se explica.
2. Abrir `tests/test_dao.py` → `PruebasCasosBorde.test_llave_foranea_invalida`. *"Intentamos guardar un pedido de un estudiante con id 99999, que no existe. Como las llaves foráneas están activadas, SQLite lo rechaza; el DAO lo convierte en `ReferenciaInvalida`, y comprobamos que no quedó ningún pedido a medias."*
3. Mencionar: *"Todas usan una base `:memory:`, que se crea vacía en cada prueba. Hay un test de CRUD por cada DAO y 6 reglas de negocio, por ejemplo que no se puede vender más de lo que hay."*
4. Señalar el final: **`Ran 87 tests ... OK`**.

### Min 9–12 · Ataques en vivo
1. Cerrar sesión → en el login escribir `' OR '1'='1` en correo y contraseña → **"Correo o contraseña incorrectos"**. *"No entra porque la consulta usa `?`: el texto se busca como un correo y nunca se ejecuta como SQL."* Mostrar en `dao/usuario_dao.py` el `WHERE correo = ?`.
2. Entrar como admin → nuevo producto con precio **`-3`** → *"El precio no puede ser negativo"*. Luego precio **`tres`** → *"debe ser un número"*. *"La propiedad `precio` de la clase `Producto` lo rechaza antes de llegar a la base."*
3. Si sobra tiempo, abrir `SEGURIDAD.md` y la tabla `usuarios` en DB Browser: solo se ven *hashes*.

### Min 12–15 · Preguntas

## Preguntas probables y respuestas cortas

- **¿Qué es el DAO?** Una capa que es la única que habla con la base. Los servicios le piden objetos y no saben nada de SQL. Si cambiáramos a MySQL, solo cambiaría esa capa.
- **¿Por qué la interfaz es una clase abstracta?** Obliga a los cuatro DAO a tener los mismos métodos CRUD. Si falta uno, Python no deja crear el objeto (`TypeError`).
- **¿Qué hace `with self._conexion() as con:`?** Abre una transacción: si el bloque termina bien, hace commit; si hay un error, hace rollback y no se guarda nada. También convierte los errores de SQLite en excepciones nuestras con mensajes claros.
- **¿Para qué `PRAGMA foreign_keys = ON`?** SQLite trae las llaves foráneas apagadas. Sin esa línea, dejaría guardar un pedido de un usuario que no existe.
- **¿Qué es `:memory:`?** Una base que vive en la RAM: rápida, vacía al empezar y que no deja archivos. Así cada prueba es independiente.
- **¿Por qué `' OR '1'='1` no funciona?** Si se pegara el texto al SQL, la condición quedaría "siempre verdadera". Con `?`, SQLite recibe el texto como un dato y no como código, así que busca un correo que se llama literalmente `' OR '1'='1`.
- **¿Dónde se valida?** En dos capas: primero en Python (propiedades de los modelos y los servicios), antes del DAO; y como respaldo, las reglas `CHECK` y `NOT NULL` de la base.
- **¿Qué ve el usuario si algo falla?** Una página "Algo salió mal". El detalle técnico solo queda en el registro del servidor, porque `DEBUG` está apagado.
- **¿Cómo se guardan las contraseñas?** Con `generate_password_hash` de werkzeug. No se pueden revertir; para iniciar sesión se compara con `check_password_hash`.
- **Muéstrame una regla de negocio probada.** `tests/test_reglas_negocio.py` → `test_no_se_vende_mas_de_lo_que_hay_y_no_queda_nada_a_medias`: si otra persona compra antes, el pedido no se guarda y el inventario no queda negativo.

## Si algo sale mal en vivo
- **El servidor no arranca porque el puerto está ocupado:** cierra la otra terminal donde corre `py app.py`.
- **"Demasiados intentos" en el login:** es el bloqueo de 5 minutos (¡también es seguridad!). Entra con la otra cuenta.
- **Una prueba falla:** lean el nombre de la prueba en voz alta y expliquen qué revisa. Pero corran las pruebas antes de entrar para que no pase.
