"""Pruebas automáticas.  Ejecutar desde la carpeta del proyecto con:

    python -m unittest discover pruebas -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import crear_app                      # noqa: E402
from config import Configuracion               # noqa: E402
from modelos import (Almuerzo, Carrito, DatosInvalidos, Estudiante,  # noqa: E402
                     InventarioInsuficiente, ProductoTienda, Usuario,
                     Administrador, ContrasenaInvalida)
from seguridad import LimitadorIntentos        # noqa: E402


# ======================================================================
# 1. Pruebas de las clases (sin servidor)
# ======================================================================
class PruebasModelos(unittest.TestCase):

    def test_usuario_es_abstracto(self):
        with self.assertRaises(TypeError):
            Usuario("x", "x@x.com", "h", "p", "r")

    def test_contrasena_se_guarda_como_hash(self):
        e = Estudiante.crear("Ana López", "ana@kiuvo.com", "Clave1234", "p", "Pupusas")
        self.assertNotIn("Clave1234", e.password_hash)
        self.assertTrue(e.verificar_contrasena("Clave1234"))
        self.assertFalse(e.verificar_contrasena("otra"))
        self.assertTrue(e.verificar_respuesta("  pupusas "))

    def test_contrasena_privada(self):
        e = Estudiante.crear("Ana López", "ana@kiuvo.com", "Clave1234", "p", "r")
        with self.assertRaises(AttributeError):
            e.__password_hash
        with self.assertRaises(AttributeError):
            e.password_hash = "nuevo"          # propiedad de solo lectura

    def test_reglas_de_contrasena(self):
        for mala in ("corta1", "sinnumeros", "12345678"):
            with self.assertRaises(ContrasenaInvalida):
                Estudiante.crear("Ana López", "a@k.com", mala, "p", "r")

    def test_polimorfismo_usuarios(self):
        e = Estudiante.crear("Ana", "a@k.com", "Clave1234", "p", "r")
        a = Administrador.crear("Admin", "b@k.com", "Clave1234", "p", "r")
        self.assertTrue(e.puede_comprar())
        self.assertFalse(a.puede_comprar())
        self.assertNotEqual(e.pagina_principal(), a.pagina_principal())

    def test_polimorfismo_productos(self):
        al = Almuerzo("Pollo", "", "Plato del día", 3.5, 10, incluye="Arroz")
        pt = ProductoTienda("Agua", "", "Bebidas", 0.75, 10, presentacion="600 ml")
        self.assertEqual(al.texto_boton(), "Reservar")
        self.assertEqual(pt.texto_boton(), "Agregar al carrito")

    def test_validaciones_producto(self):
        with self.assertRaises(DatosInvalidos):
            Almuerzo("Pollo", "", "Plato del día", -1, 10)
        with self.assertRaises(DatosInvalidos):
            Almuerzo("Pollo", "", "Bebidas", 3, 10)      # categoría de otro tipo
        with self.assertRaises(DatosInvalidos):
            ProductoTienda("Agua", "", "Bebidas", 1, -5)

    def test_carrito_no_supera_existencias(self):
        p = ProductoTienda("Agua", "", "Bebidas", 0.75, 2, id=1)
        c = Carrito()
        c.agregar(p, 2)
        self.assertEqual(c.total, 1.5)
        with self.assertRaises(InventarioInsuficiente):
            c.agregar(p, 1)

    def test_limitador_intentos(self):
        ahora = [0]
        lim = LimitadorIntentos(3, 60, reloj=lambda: ahora[0])
        for _ in range(3):
            lim.registrar_fallo("x")
        self.assertGreater(lim.segundos_restantes("x"), 0)
        ahora[0] = 61
        self.assertEqual(lim.segundos_restantes("x"), 0)


# ======================================================================
# 2. Pruebas del sitio completo (con un navegador simulado)
# ======================================================================
class BaseSitio(unittest.TestCase):
    """Prepara un sitio con base de datos temporal (sin pruebas propias)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()

        class ConfigPruebas(Configuracion):
            TESTING = True
            BASE_DATOS = os.path.join(self.carpeta.name, "prueba.db")

        self.app = crear_app(ConfigPruebas)
        self.cliente = self.app.test_client()
        self.c = self.app.extensions["kiuvo"]

    def tearDown(self):
        self.carpeta.cleanup()

    # ---------- ayudantes ----------
    def token(self, url="/login"):
        html = self.cliente.get(url).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)

    def post(self, url, datos=None, pagina="/login", **kw):
        datos = dict(datos or {})
        datos["csrf_token"] = self.token(pagina)
        return self.cliente.post(url, data=datos, **kw)

    def entrar(self, correo, contrasena):
        return self.post("/login", {"correo": correo, "contrasena": contrasena},
                         follow_redirects=True)

    def entrar_estudiante(self):
        return self.entrar("estudiante@kiuvo.com", "Estudiante2026")

    def entrar_admin(self):
        return self.entrar("admin@kiuvo.com", "Kiuvo2026")

    def producto(self, nombre):
        return next(p for p in self.c.productos.listar() if p.nombre == nombre)


class PruebasSitio(BaseSitio):

    # ---------- seguridad ----------
    def test_post_sin_csrf_es_rechazado(self):
        r = self.cliente.post("/login", data={"correo": "x", "contrasena": "y"})
        self.assertEqual(r.status_code, 400)

    def test_encabezados_de_seguridad(self):
        r = self.cliente.get("/")
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])

    def test_bloqueo_tras_cinco_intentos(self):
        for _ in range(5):
            r = self.entrar("estudiante@kiuvo.com", "mala")
        self.assertIn("Demasiados intentos", r.get_data(as_text=True))
        r = self.entrar_estudiante()        # ni con la correcta mientras dure el bloqueo
        self.assertIn("Demasiados intentos", r.get_data(as_text=True))

    def test_paginas_protegidas_piden_login(self):
        for url in ("/almuerzos", "/carrito", "/mis-pedidos", "/admin/"):
            r = self.cliente.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login", r.headers["Location"])

    def test_admin_no_puede_comprar(self):
        self.entrar_admin()
        self.assertEqual(self.cliente.get("/almuerzos").status_code, 403)
        pid = self.producto("Agua embotellada").id
        r = self.post(f"/carrito/agregar/{pid}", {"cantidad": 1}, pagina="/admin/")
        self.assertEqual(r.status_code, 403)

    def test_estudiante_no_entra_al_admin(self):
        self.entrar_estudiante()
        self.assertEqual(self.cliente.get("/admin/inventario").status_code, 403)

    # ---------- registro y recuperación ----------
    def test_registro_valida_y_crea_estudiante(self):
        datos = {"nombre": "Ana López", "correo": "ana@kiuvo.com", "contrasena": "corta",
                 "confirmacion": "corta", "pregunta": Usuario.PREGUNTAS_SEGURIDAD[0],
                 "respuesta": "Firulais"}
        r = self.post("/registro", datos, pagina="/registro")
        self.assertIn("al menos 8", r.get_data(as_text=True))
        datos.update(contrasena="Clave1234", confirmacion="Clave1234")
        r = self.post("/registro", datos, pagina="/registro", follow_redirects=True)
        self.assertIn("Almuerzos", r.get_data(as_text=True))
        u = self.c.usuarios.buscar_por_correo("ana@kiuvo.com")
        self.assertIsInstance(u, Estudiante)

    def test_olvide_mi_contrasena(self):
        r = self.post("/recuperar", {"correo": "estudiante@kiuvo.com"}, pagina="/recuperar",
                      follow_redirects=True)
        self.assertIn("comida favorita", r.get_data(as_text=True))
        r = self.post("/recuperar/pregunta", {"respuesta": "tacos", "contrasena": "Nueva2026",
                                              "confirmacion": "Nueva2026"},
                      pagina="/recuperar/pregunta")
        self.assertIn("no es correcta", r.get_data(as_text=True))
        r = self.post("/recuperar/pregunta", {"respuesta": "PUPUSAS", "contrasena": "Nueva2026",
                                              "confirmacion": "Nueva2026"},
                      pagina="/recuperar/pregunta", follow_redirects=True)
        self.assertIn("se cambió", r.get_data(as_text=True))
        self.assertIn("Mis pedidos", self.entrar("estudiante@kiuvo.com", "Nueva2026").get_data(as_text=True))

    # ---------- catálogo e inventario ----------
    def test_estudiante_solo_ve_disponibles(self):
        self.entrar_estudiante()
        html = self.cliente.get("/almuerzos").get_data(as_text=True)
        self.assertIn("Pollo guisado", html)
        self.assertNotIn("Wrap integral", html)          # agotado
        html = self.cliente.get("/tienda").get_data(as_text=True)
        self.assertNotIn("Quesadilla salvadoreña", html)  # agotado

    def test_admin_ve_todo_el_inventario(self):
        self.entrar_admin()
        html = self.cliente.get("/admin/inventario").get_data(as_text=True)
        self.assertIn("Wrap integral", html)
        self.assertIn("Agotado", html)

    def test_filtro_por_categoria(self):
        self.entrar_estudiante()
        html = self.cliente.get("/almuerzos?categoria=Vegetariano").get_data(as_text=True)
        self.assertIn("Lasaña de vegetales", html)
        self.assertNotIn("Pollo guisado", html)
        self.assertIn('href="/almuerzos?categoria=Ligero"', html)   # se queda en almuerzos

    def test_admin_crea_edita_oculta_y_repone(self):
        self.entrar_admin()
        r = self.post("/admin/productos/nuevo/tienda",
                      {"nombre": "Horchata", "descripcion": "", "categoria": "Bebidas",
                       "precio": "1.10", "existencias": "15", "presentacion": "Vaso 16 oz"},
                      pagina="/admin/", follow_redirects=True)
        self.assertIn("Horchata", r.get_data(as_text=True))
        p = self.producto("Horchata")
        self.post(f"/admin/productos/{p.id}/editar",
                  {"nombre": "Horchata de morro", "descripcion": "", "categoria": "Bebidas",
                   "precio": "1.25", "existencias": "15", "presentacion": "Vaso 16 oz"},
                  pagina="/admin/")
        self.assertEqual(self.c.productos.buscar_por_id(p.id).precio, 1.25)
        self.post(f"/admin/productos/{p.id}/visibilidad", pagina="/admin/")
        self.assertFalse(self.c.productos.buscar_por_id(p.id).activo)
        self.post(f"/admin/productos/{p.id}/reponer", {"cantidad": 5}, pagina="/admin/")
        self.assertEqual(self.c.productos.buscar_por_id(p.id).existencias, 20)
        r = self.post("/admin/productos/nuevo/tienda",
                      {"nombre": "Mala", "categoria": "Bebidas", "precio": "-3", "existencias": "1"},
                      pagina="/admin/")
        self.assertIn("negativo", r.get_data(as_text=True))

    # ---------- compra y cancelación ----------
    def test_compra_descuenta_y_cancelar_devuelve(self):
        self.entrar_estudiante()
        pollo = self.producto("Pollo guisado")
        agua = self.producto("Agua embotellada")
        self.post(f"/carrito/agregar/{pollo.id}", {"cantidad": 2}, pagina="/almuerzos")
        self.post(f"/carrito/agregar/{agua.id}", {"cantidad": 1}, pagina="/tienda")
        html = self.cliente.get("/carrito").get_data(as_text=True)
        self.assertIn("$7.75", html)

        r = self.post("/pagar", {"metodo": "tarjeta"}, pagina="/pagar", follow_redirects=True)
        texto = r.get_data(as_text=True)
        self.assertIn("Pago simulado aprobado", texto)
        self.assertEqual(self.c.productos.buscar_por_id(pollo.id).existencias, pollo.existencias - 2)

        pedido = self.c.pedidos.listar()[0]
        self.assertEqual(pedido.total, 7.75)
        self.post(f"/mis-pedidos/{pedido.id}/cancelar", pagina="/mis-pedidos")
        self.assertEqual(self.c.productos.buscar_por_id(pollo.id).existencias, pollo.existencias)
        r = self.post(f"/mis-pedidos/{pedido.id}/cancelar", pagina="/mis-pedidos", follow_redirects=True)
        self.assertIn("ya no se puede cancelar", r.get_data(as_text=True))

    def test_no_se_puede_comprar_mas_de_lo_disponible(self):
        self.entrar_estudiante()
        ensalada = self.producto("Ensalada César con pollo")   # solo hay 4
        r = self.post(f"/carrito/agregar/{ensalada.id}", {"cantidad": 9},
                      pagina="/almuerzos", follow_redirects=True)
        self.assertIn("No hay suficiente inventario", r.get_data(as_text=True))

    def test_inventario_cambia_mientras_esta_en_el_carrito(self):
        self.entrar_estudiante()
        chips = self.producto("Chips de plátano")             # hay 8
        self.post(f"/carrito/agregar/{chips.id}", {"cantidad": 8}, pagina="/tienda")
        chips.existencias = 3                                  # otra persona compró
        self.c.productos.actualizar(chips)
        html = self.cliente.get("/carrito").get_data(as_text=True)
        self.assertIn("se ajustó la cantidad", html)

    def test_no_puede_cancelar_pedido_ajeno(self):
        self.entrar_estudiante()
        agua = self.producto("Agua embotellada")
        self.post(f"/carrito/agregar/{agua.id}", {"cantidad": 1}, pagina="/tienda")
        self.post("/pagar", {"metodo": "caja"}, pagina="/pagar")
        pedido_id = self.c.pedidos.listar()[0].id
        self.post("/logout", pagina="/")
        datos = {"nombre": "Otra Persona", "correo": "otra@kiuvo.com", "contrasena": "Clave1234",
                 "confirmacion": "Clave1234", "pregunta": Usuario.PREGUNTAS_SEGURIDAD[0],
                 "respuesta": "x y"}
        self.post("/registro", datos, pagina="/registro")
        r = self.post(f"/mis-pedidos/{pedido_id}/cancelar", pagina="/mis-pedidos",
                      follow_redirects=True)
        self.assertIn("No encontramos ese pedido", r.get_data(as_text=True))

    def test_todas_las_paginas_cargan(self):
        self.assertEqual(self.cliente.get("/").status_code, 200)
        self.assertEqual(self.cliente.get("/registro").status_code, 200)
        self.assertEqual(self.cliente.get("/recuperar").status_code, 200)
        self.assertEqual(self.cliente.get("/no-existe").status_code, 404)
        self.entrar_admin()
        for url in ("/admin/", "/admin/inventario", "/admin/inventario?tipo=almuerzo",
                    "/admin/inventario?tipo=tienda&categoria=Snacks", "/admin/pedidos",
                    "/admin/productos/nuevo/almuerzo", "/admin/productos/1/editar"):
            self.assertEqual(self.cliente.get(url).status_code, 200, url)


# ======================================================================
# 3. Pruebas de la base de datos normalizada
# ======================================================================
ESQUEMA_VERSION_1 = """
CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, rol TEXT NOT NULL,
    pregunta_seguridad TEXT NOT NULL, respuesta_hash TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
CREATE TABLE productos (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL,
    nombre TEXT NOT NULL, descripcion TEXT NOT NULL DEFAULT '', categoria TEXT NOT NULL,
    precio REAL NOT NULL, existencias INTEGER NOT NULL, activo INTEGER NOT NULL DEFAULT 1,
    incluye TEXT, presentacion TEXT);
CREATE TABLE pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id), fecha TEXT NOT NULL,
    estado TEXT NOT NULL, metodo_pago TEXT NOT NULL, total REAL NOT NULL);
CREATE TABLE detalle_pedido (id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id), nombre_producto TEXT NOT NULL,
    precio_unitario REAL NOT NULL, cantidad INTEGER NOT NULL);
INSERT INTO usuarios VALUES (1, 'Ana', 'ana@k.com', 'h', 'estudiante', 'p', 'r', '2026-10-01');
INSERT INTO productos VALUES (1, 'almuerzo', 'Pollo', '', 'Plato del día', 3.5, 10, 1, 'Arroz', NULL);
INSERT INTO productos VALUES (2, 'tienda', 'Agua', '', 'Bebidas', 0.75, 20, 1, NULL, '600 ml');
INSERT INTO productos VALUES (3, 'tienda', 'Jugo', '', 'Bebidas', 1.25, 5, 0, NULL, '350 ml');
INSERT INTO pedidos VALUES (1, 1, '2026-10-01 12:00', 'pendiente', 'caja', 4.25);
INSERT INTO detalle_pedido VALUES (1, 1, 1, 'Pollo', 3.5, 1);
INSERT INTO detalle_pedido VALUES (2, 1, 2, 'Agua', 0.75, 1);
"""


class BaseBD(unittest.TestCase):
    """Prepara una base de datos temporal (sin pruebas propias)."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "prueba.db")

    def tearDown(self):
        self.carpeta.cleanup()

    def iniciar(self):
        from base_datos import BaseDatos
        from datos_iniciales import cargar_datos_iniciales
        from dao import CategoriaDAO, PedidoDAO, ProductoDAO, UsuarioDAO
        bd = BaseDatos(self.ruta)
        bd.inicializar()
        self.bd = bd
        self.usuarios = UsuarioDAO(bd)
        self.categorias = CategoriaDAO(bd)
        self.productos = ProductoDAO(bd)
        self.pedidos = PedidoDAO(bd)
        cargar_datos_iniciales(self.usuarios, self.categorias, self.productos)

    def consulta(self, sql, parametros=()):
        with self.bd.conexion() as con:
            return [tuple(f) for f in con.execute(sql, parametros).fetchall()]


class PruebasBaseDatosNormalizada(BaseBD):

    def test_tablas_separadas(self):
        self.iniciar()
        tablas = {t for (t,) in self.consulta("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"categorias", "productos", "almuerzos", "productos_tienda"} <= tablas)
        columnas = {c[1] for c in self.consulta("PRAGMA table_info(productos)")}
        self.assertNotIn("categoria", columnas)      # ya no hay texto repetido
        self.assertNotIn("incluye", columnas)        # ni columnas que quedan vacías
        self.assertIn("categoria_id", columnas)

    def test_cada_categoria_se_guarda_una_vez(self):
        self.iniciar()
        filas = self.consulta("SELECT nombre, COUNT(*) FROM categorias GROUP BY nombre, tipo")
        self.assertEqual(len(filas), 6)
        self.assertTrue(all(n == 1 for _, n in filas))

    def test_cada_producto_en_su_tabla_de_detalle(self):
        self.iniciar()
        sin_detalle = self.consulta("""
            SELECT p.id FROM productos p
            LEFT JOIN almuerzos a ON a.producto_id = p.id
            LEFT JOIN productos_tienda t ON t.producto_id = p.id
            WHERE (p.tipo = 'almuerzo' AND a.producto_id IS NULL)
               OR (p.tipo = 'tienda' AND t.producto_id IS NULL)""")
        self.assertEqual(sin_detalle, [])
        pollo = next(p for p in self.productos.listar() if p.nombre == "Pollo guisado")
        self.assertEqual(pollo.incluye, "Arroz, ensalada y fresco")

    def test_editar_actualiza_la_tabla_de_detalle(self):
        self.iniciar()
        agua = next(p for p in self.productos.listar() if p.nombre == "Agua embotellada")
        agua.presentacion = "Botella 1 L"
        agua.categoria = "Snacks"
        self.productos.actualizar(agua)
        recargada = self.productos.buscar_por_id(agua.id)
        self.assertEqual(recargada.presentacion, "Botella 1 L")
        self.assertEqual(recargada.categoria, "Snacks")
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM productos_tienda WHERE producto_id = ?",
                                       (agua.id,)), [(1,)])

    def test_la_base_impide_categoria_de_otro_tipo(self):
        import sqlite3
        self.iniciar()
        (bebidas_id,) = self.consulta("SELECT id FROM categorias WHERE nombre = 'Bebidas'")[0]
        with self.assertRaises(sqlite3.IntegrityError):
            with self.bd.conexion() as con:
                con.execute("INSERT INTO productos (tipo, nombre, categoria_id, precio, existencias) "
                            "VALUES ('almuerzo', 'Truco', ?, 1, 1)", (bebidas_id,))

    def test_migra_una_base_de_la_version_1(self):
        import sqlite3
        con = sqlite3.connect(self.ruta)
        con.executescript(ESQUEMA_VERSION_1)
        con.close()

        self.iniciar()
        self.assertEqual(self.consulta("PRAGMA user_version"), [(2,)])
        pollo, agua, jugo = (self.productos.buscar_por_id(i) for i in (1, 2, 3))
        self.assertIsInstance(pollo, Almuerzo)
        self.assertEqual((pollo.categoria, pollo.incluye), ("Plato del día", "Arroz"))
        self.assertEqual((agua.categoria, agua.presentacion), ("Bebidas", "600 ml"))
        self.assertFalse(jugo.activo)
        # "Bebidas" estaba escrita dos veces; ahora es una sola fila
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM categorias WHERE nombre = 'Bebidas'"), [(1,)])
        # los pedidos viejos siguen apuntando a los mismos productos
        self.assertEqual(self.consulta("SELECT producto_id FROM detalle_pedido ORDER BY id"), [(1,), (2,)])
        self.assertEqual(self.consulta("PRAGMA foreign_key_check"), [])
        # y no se volvieron a cargar los productos de ejemplo encima
        self.assertEqual(self.productos.contar(), 3)


# ======================================================================
# 4. Capa DAO: interfaz, CRUD completo y manejo de excepciones
# ======================================================================
class PruebasDAO(BaseBD):

    def test_dao_es_una_interfaz_abstracta(self):
        from dao import DAO, CategoriaDAO, PedidoDAO, ProductoDAO, UsuarioDAO
        with self.assertRaises(TypeError):
            DAO(None)                                     # no se puede instanciar
        for clase in (UsuarioDAO, CategoriaDAO, ProductoDAO, PedidoDAO):
            self.assertTrue(issubclass(clase, DAO))
            for metodo in ("insertar", "buscar_por_id", "listar", "actualizar", "eliminar"):
                self.assertTrue(callable(getattr(clase, metodo)))

    def test_crud_completo_de_productos(self):
        self.iniciar()
        nuevo = self.productos.insertar(ProductoTienda("Horchata", "", "Bebidas", 1.1, 10,
                                                       presentacion="Vaso 16 oz"))     # C
        leido = self.productos.buscar_por_id(nuevo.id)                                  # R
        self.assertEqual(leido.presentacion, "Vaso 16 oz")
        leido.precio = 1.25
        self.productos.actualizar(leido)                                               # U
        self.assertEqual(self.productos.buscar_por_id(nuevo.id).precio, 1.25)
        self.productos.eliminar(nuevo.id)                                              # D
        self.assertIsNone(self.productos.buscar_por_id(nuevo.id))
        # la fila de productos_tienda también se borró (ON DELETE CASCADE)
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM productos_tienda WHERE producto_id = ?",
                                       (nuevo.id,)), [(0,)])

    def test_crud_de_categorias_y_usuarios(self):
        from modelos import Categoria
        self.iniciar()
        cat = self.categorias.insertar(Categoria("Desayunos", "almuerzo"))
        cat.nombre = "Desayunos típicos"
        self.categorias.actualizar(cat)
        self.assertEqual(self.categorias.buscar_por_id(cat.id).nombre, "Desayunos típicos")
        self.categorias.eliminar(cat.id)
        self.assertIsNone(self.categorias.buscar_por_id(cat.id))

        u = self.usuarios.insertar(Estudiante.crear("Ana López", "ana@k.com", "Clave1234", "p", "r"))
        self.assertEqual(self.usuarios.buscar_por_correo("ANA@k.com").id, u.id)
        self.usuarios.eliminar(u.id)
        self.assertIsNone(self.usuarios.buscar_por_id(u.id))

    def test_errores_de_sqlite_se_convierten_en_excepciones_propias(self):
        from modelos import (Categoria, ErrorBaseDatos, RegistroDuplicado, RegistroEnUso,
                             RegistroNoEncontrado)
        self.iniciar()
        with self.assertRaises(RegistroDuplicado) as ctx:
            self.categorias.insertar(Categoria("Bebidas", "tienda"))
        self.assertIn("Ya existe", str(ctx.exception))
        with self.assertRaises(RegistroEnUso):
            bebidas = next(c for c in self.categorias.listar() if c.nombre == "Bebidas")
            self.categorias.eliminar(bebidas.id)          # hay productos que la usan
        with self.assertRaises(RegistroNoEncontrado):
            self.productos.eliminar(99999)
        self.assertTrue(issubclass(RegistroDuplicado, ErrorBaseDatos))

    def test_no_se_elimina_un_producto_ya_vendido(self):
        from modelos import Pedido, ItemPedido, RegistroEnUso
        self.iniciar()
        agua = next(p for p in self.productos.listar() if p.nombre == "Agua embotellada")
        alumno = self.usuarios.buscar_por_correo("estudiante@kiuvo.com")
        self.pedidos.insertar(Pedido(alumno.id, [ItemPedido(agua.id, agua.nombre, agua.precio, 1)], "caja"))
        with self.assertRaises(RegistroEnUso) as ctx:
            self.productos.eliminar(agua.id)
        self.assertIn("ocultarlo", str(ctx.exception))
        self.assertIsNotNone(self.productos.buscar_por_id(agua.id))

    def test_la_base_rechaza_nombres_repetidos(self):
        from modelos import RegistroDuplicado
        self.iniciar()
        with self.assertRaises(RegistroDuplicado):
            self.productos.insertar(ProductoTienda("BROWNIE", "", "Postres", 1, 1))


class PruebasValidaciones(BaseSitio):

    def test_admin_elimina_producto_sin_ventas(self):
        self.entrar_admin()
        cafe = self.producto("Café americano")
        r = self.cliente.get(f"/admin/productos/{cafe.id}/eliminar")
        self.assertIn("¿Eliminar", r.get_data(as_text=True))
        r = self.post(f"/admin/productos/{cafe.id}/eliminar", pagina="/admin/", follow_redirects=True)
        self.assertIn("se eliminó", r.get_data(as_text=True))
        self.assertIsNone(self.c.productos.buscar_por_id(cafe.id))

    def test_admin_no_elimina_producto_vendido(self):
        self.entrar_estudiante()
        agua = self.producto("Agua embotellada")
        self.post(f"/carrito/agregar/{agua.id}", {"cantidad": 1}, pagina="/tienda")
        self.post("/pagar", {"metodo": "caja"}, pagina="/pagar")
        self.post("/logout", pagina="/")
        self.entrar_admin()
        r = self.post(f"/admin/productos/{agua.id}/eliminar", pagina="/admin/", follow_redirects=True)
        self.assertIn("Puedes ocultarlo", r.get_data(as_text=True))

    def test_producto_duplicado_rechazado(self):
        self.entrar_admin()
        r = self.post("/admin/productos/nuevo/tienda",
                      {"nombre": "  brownie ", "categoria": "Postres", "precio": "2", "existencias": "3"},
                      pagina="/admin/")
        self.assertIn("Ya existe un producto de tienda llamado", r.get_data(as_text=True))
        pollo = self.producto("Pollo guisado")                # editar con el nombre de otro
        r = self.post(f"/admin/productos/{pollo.id}/editar",
                      {"nombre": "Carne asada", "categoria": "Plato del día", "precio": "3", "existencias": "3"},
                      pagina="/admin/")
        self.assertIn("Ya existe un almuerzo llamado", r.get_data(as_text=True))

    def test_vacios_tipos_y_rangos(self):
        self.entrar_admin()
        casos = [
            ({"nombre": "", "categoria": "Bebidas", "precio": "1", "existencias": "1"}, "no puede estar vacío"),
            ({"nombre": "X", "categoria": "Bebidas", "precio": "", "existencias": "1"}, "Escribe el precio"),
            ({"nombre": "X", "categoria": "Bebidas", "precio": "abc", "existencias": "1"}, "debe ser un número"),
            ({"nombre": "X", "categoria": "Bebidas", "precio": "500", "existencias": "1"}, "no puede ser mayor"),
            ({"nombre": "X", "categoria": "Bebidas", "precio": "1", "existencias": "2.5"}, "sin decimales"),
            ({"nombre": "X", "categoria": "Bebidas", "precio": "1", "existencias": "100000"}, "no pueden pasar de"),
        ]
        for datos, esperado in casos:
            r = self.post("/admin/productos/nuevo/tienda", datos, pagina="/admin/")
            self.assertIn(esperado, r.get_data(as_text=True), datos)

    def test_login_vacio_no_cuenta_como_intento(self):
        for _ in range(6):
            r = self.entrar("", "")
        texto = r.get_data(as_text=True)
        self.assertIn("Escribe tu correo y tu contraseña", texto)
        self.assertNotIn("Demasiados intentos", self.entrar_estudiante().get_data(as_text=True))

    def test_registro_con_mensajes_claros(self):
        base = {"nombre": "Ana López", "correo": "ana@kiuvo.com", "contrasena": "Clave1234",
                "confirmacion": "Clave1234", "pregunta": Usuario.PREGUNTAS_SEGURIDAD[0], "respuesta": "Firulais"}
        casos = [({"nombre": ""}, "Escribe tu nombre"), ({"nombre": "Ana123"}, "solo puede tener letras"),
                 ({"correo": ""}, "Escribe tu correo"), ({"correo": "ana@"}, "correo válido"),
                 ({"correo": "estudiante@kiuvo.com"}, "Ya existe una cuenta")]
        for cambio, esperado in casos:
            r = self.post("/registro", {**base, **cambio}, pagina="/registro")
            self.assertIn(esperado, r.get_data(as_text=True), cambio)

    def test_error_de_base_de_datos_muestra_mensaje(self):
        import sqlite3
        from unittest import mock
        self.entrar_admin()
        with mock.patch.object(self.c.base_datos, "_conectar",
                               side_effect=sqlite3.OperationalError("disk I/O error")):
            r = self.cliente.get("/admin/inventario")
        self.assertEqual(r.status_code, 503)
        self.assertIn("No se pudo acceder a la base de datos", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
