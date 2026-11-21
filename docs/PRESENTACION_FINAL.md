# Presentación final: guion de 10 minutos

Se califica **lo que se muestra en pantalla**. A los 10:00 se corta, y lo que no se mostró no cuenta. Son 100 puntos: funcionalidad (25), persistencia (20), diseño OO (20), validaciones y errores (15), comunicación y defensa (20).

## Las 6 evidencias obligatorias y cómo las cumplimos

| # | Evidencia | Qué mostramos | Dónde está en el código |
|---|---|---|---|
| 1 | Crear un registro desde la interfaz | El admin crea el producto "Horchata" | `ServicioInventario.crear` → `ProductoDAO.insertar` |
| 2 | Cerrar, reabrir y que siga ahí | Ctrl + C, `py app.py` otra vez, y la Horchata sigue en el inventario | Archivo `instancia/kiuvo.db` (SQLite) |
| 3 | Consulta propia del negocio | **Reporte mensual de ventas** (y "Necesitan atención" en el panel) | `PedidoDAO.reporte_mensual` (`GROUP BY` + `SUM`) y `ProductoDAO.listar_existencias_bajas` |
| 4 | Operación de varios pasos en transacción | Un estudiante compra: se guarda el pedido, se descuenta el inventario y se guardan sus líneas, todo o nada | `PedidoDAO.insertar` dentro de `with self._conexion() as con:` |
| 5 | Provocar un error y mostrar cómo se maneja | Precio `-3` y un código de recibo que no existe (`KV-ZZZZZZ`): mensaje claro y el sitio sigue funcionando | Propiedad `Producto.precio`, `Pedido.normalizar_codigo`, excepciones `DatosInvalidos` y `RegistroNoEncontrado` |
| 6 | Diagrama de clases final | `docs/diagrama_clases.png` señalando herencia, polimorfismo e interfaz DAO | `docs/diagrama_clases_1_modelo.png`, `_2_dao.png`, `_3_servicios.png` |

## Antes de empezar (el montaje no puede pasar de 1 minuto)

- [ ] `git pull` y `py -m unittest` en la compu que se va a usar (debe salir `OK`).
- [ ] `py app.py` encendido, con **datos de prueba**: 3 o 4 compras hechas antes, una ya marcada como **Entregado** y otra como **No recogido**, para que el reporte del mes tenga datos.
- [ ] Ventana normal de Chrome con sesión de **admin** y una ventana de **incógnito** (Ctrl + Shift + N) con sesión de **estudiante**.
- [ ] VS Code abierto en `dao/pedido_dao.py`, y el diagrama `docs/diagrama_clases.png` abierto.
- [ ] Plan B: un video grabado de la demo. Si se usa, el criterio 1 llega máximo a 20 de 25.

## Guion

### 0:00–1:00 · Contexto
> "La cafetería de Key Institute tiene filas largas a la hora del almuerzo, y la gerente arma a mano los cuadros de ventas a fin de mes. Menú KIUVO deja que los estudiantes reserven y paguen antes, y que la cafetería entregue con un código de recibo y vea sus ventas del mes. Lo hicimos en Python con Flask, programado con clases, y guarda todo en SQLite."

### 1:00–6:00 · Demo en vivo
1. **Evidencia 1 (admin):** Inventario → **+ Producto de tienda** → "Horchata", Bebidas, $1.00, 10 → Guardar.
2. **Evidencia 2:** en la terminal, **Ctrl + C** y `py app.py`. Recargar el inventario: la Horchata sigue ahí.
   > "Se guardó en el archivo `kiuvo.db`. Los datos no viven en la memoria."
3. **Evidencia 4 (estudiante, en incógnito):** Tienda → agregar 2 Horchatas → Carrito → Pagar.
   - Sale el **recibo** con su código, por ejemplo `KV-7F3K9Q`, y el aviso "La cafetería ya recibió tu pedido".
   > "Esto es una transacción: en un solo paso se guarda el pedido, se descuentan las 2 horchatas del inventario y se guardan las líneas del pedido. Si algo falla, no se guarda nada."
   - En la ventana del admin, el inventario de Horchata baja de 10 a 8.
4. **Entrega (admin):** Pedidos → escribir el código del recibo → Buscar → **Entregado**.
   > "Así la cafetería sabe quién retiró y quién pagó y no llegó."
5. **Evidencia 3 (admin):** Reportes → mes actual.
   > "Esta es nuestra consulta propia: suma con `GROUP BY` lo vendido de cada producto en el mes, sin contar los cancelados. Es lo que la gerente necesita a fin de mes, y se descarga para Excel."
   - Clic en **Descargar para Excel**.
6. **Evidencia 5 (admin):**
   - Nuevo producto con precio **`-3`** → "El precio no puede ser negativo".
   - Pedidos → buscar **`KV-ZZZZZZ`** → "No hay ningún pedido con el código KV-ZZZZZZ".
   > "El sistema lanza una excepción del negocio, la ruta la atrapa con `try/except`, muestra un mensaje claro y sigue funcionando. El usuario nunca ve un error técnico."

### 6:00–8:00 · Código y diseño
1. **Evidencia 6:** abrir `docs/diagrama_clases.png` y señalar:
   - **Herencia:** `Usuario` → `Estudiante` y `Administrador`; `Producto` → `Almuerzo` y `ProductoTienda`.
   - **Polimorfismo:** `puede_comprar()` responde distinto en cada usuario; `MetodoPago.procesar()` responde distinto en caja y con tarjeta.
   - **Interfaz DAO:** la clase abstracta `DAO` con el CRUD, y sus 4 implementaciones.
2. **Una clase clave:** `dao/pedido_dao.py`.
   - `insertar`: la transacción.
   - `reporte_mensual`: la consulta propia.
   - Todo con `?`: consultas parametrizadas, nunca texto pegado.

### 8:00–10:00 · Preguntas
Ver "Preguntas que pueden caerle a cualquiera" en `docs/GUIA_DEFENSA.md`. Todas deben poder responder al menos dos preguntas sobre su parte del código.

## Entregables (subir antes de la hora)
- **Código fuente:** el repositorio de GitHub (rama `main`).
- **Archivo de base de datos:** una copia de `instancia/kiuvo.db` con los datos de prueba. Esa carpeta no se sube a GitHub, así que se entrega aparte.
- **Diagrama de clases:** `docs/diagrama_clases.png`.
