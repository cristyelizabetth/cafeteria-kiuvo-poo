"""Pruebas de seguridad: inyección SQL, validación de entrada, contraseñas y errores.

Son los mismos ataques que se describen en SEGURIDAD.md.
Ejecutar:   python -m unittest tests.test_seguridad -v
"""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tests.test_cafeteria import BaseSitio       # noqa: E402
from tests.test_dao import BaseMemoria           # noqa: E402

INYECCION = "' OR '1'='1"


# ======================================================================
# 1. Inyección SQL
# ======================================================================
class PruebasInyeccionSQL(BaseSitio):

    def test_login_con_or_1_igual_1_no_entra(self):
        intentos = [
            (INYECCION, INYECCION),                     # en los dos campos
            ("admin@kiuvo.com' --", "loquesea"),        # intenta "comentar" la revisión de contraseña
            ("admin@kiuvo.com", INYECCION),             # en la contraseña
        ]
        for correo, contrasena in intentos:
            with self.subTest(correo=correo):
                texto = self.entrar(correo, contrasena).get_data(as_text=True)
                self.assertIn("Correo o contraseña incorrectos", texto)
                self.assertNotIn("Salir", texto)        # sigue sin sesión
                self.assertEqual(self.cliente.get("/admin/").status_code, 302)   # lo manda al login

    def test_la_inyeccion_se_guarda_como_texto_y_no_borra_nada(self):
        self.entrar_admin()
        nombre = "Té'); DROP TABLE productos; --"
        self.post("/admin/productos/nuevo/tienda",
                  {"nombre": nombre, "categoria": "Bebidas", "precio": "1", "existencias": "5"},
                  pagina="/admin/")
        nombres = [p.nombre for p in self.c.productos.listar()]
        self.assertIn(nombre, nombres)                  # se guardó tal cual, como texto
        self.assertIn("Agua embotellada", nombres)      # la tabla sigue ahí, con todo

    def test_scripts_en_los_datos_no_se_ejecutan(self):
        self.entrar_admin()
        nombre = "<script>alert('hackeado')</script>"
        self.post("/admin/productos/nuevo/tienda",
                  {"nombre": nombre, "categoria": "Bebidas", "precio": "1", "existencias": "5"},
                  pagina="/admin/")
        html = self.cliente.get("/admin/inventario").get_data(as_text=True)
        self.assertNotIn(nombre, html)                                  # no aparece como código
        self.assertIn("&lt;script&gt;", html)                          # aparece como texto

    def test_filtros_de_la_url_no_ejecutan_sql(self):
        self.entrar_estudiante()
        r = self.cliente.get("/tienda?categoria=" + INYECCION)
        self.assertEqual(r.status_code, 200)            # se ignora el filtro: no hay error ni datos extra


class PruebasInyeccionDAO(BaseMemoria):

    def test_dao_trata_la_inyeccion_como_texto(self):
        self.assertIsNone(self.usuarios.buscar_por_correo(INYECCION))
        self.assertFalse(self.usuarios.existe_correo(INYECCION))
        self.assertEqual(self.productos.listar(categoria=INYECCION), [])
        self.assertEqual(self.pedidos.listar(estado=INYECCION), [])
        self.assertEqual(self.usuarios.contar(), 2)     # nada cambió

    def test_todas_las_consultas_estan_en_el_dao_y_usan_parametros(self):
        """Revisa el código: fuera de dao/ y base_datos.py no hay SQL,
        y dentro de dao/ ningún valor se pega al SQL con f-strings, + o %."""
        sql = re.compile(r"\b(SELECT|INSERT INTO|UPDATE \w+ SET|DELETE FROM)\b|\.execute\(")
        archivos = [*RAIZ.glob("*.py"), *(RAIZ / "modelos").glob("*.py"), *(RAIZ / "rutas").glob("*.py")]
        for archivo in archivos:
            relativo = archivo.relative_to(RAIZ).as_posix()
            if relativo == "base_datos.py":       # crea las tablas: junto con dao/ es la capa de datos
                continue
            with self.subTest(archivo=relativo):
                self.assertIsNone(sql.search(archivo.read_text(encoding="utf-8")),
                                  f"Hay SQL fuera del DAO en {relativo}")

        for archivo in (RAIZ / "dao").glob("*.py"):
            texto = archivo.read_text(encoding="utf-8")
            for llamada in re.findall(r"\.execute\((.*?)\)\s*$", texto, re.M | re.S):
                with self.subTest(archivo=archivo.name):
                    self.assertNotRegex(llamada, r"%\s*\(|\.format\(")


# ======================================================================
# 2. Validación de entrada (antes de llegar a la base de datos)
# ======================================================================
class PruebasValidacionEntrada(BaseSitio):

    def test_producto_vacio_negativo_o_con_formato_incorrecto(self):
        self.entrar_admin()
        antes = self.c.productos.contar()
        casos = [
            ({"nombre": "   ", "precio": "1", "existencias": "1"}, "no puede estar vacío"),
            ({"nombre": "Jugo", "precio": "-3", "existencias": "1"}, "no puede ser negativo"),
            ({"nombre": "Jugo", "precio": "1", "existencias": "-4"}, "no pueden ser negativas"),
            ({"nombre": "Jugo", "precio": "tres", "existencias": "1"}, "debe ser un número"),
            ({"nombre": "Jugo", "precio": "1", "existencias": "dos"}, "número entero"),
        ]
        for datos, mensaje in casos:
            with self.subTest(datos=datos):
                datos["categoria"] = "Bebidas"
                r = self.post("/admin/productos/nuevo/tienda", datos, pagina="/admin/")
                self.assertIn(mensaje, r.get_data(as_text=True))
        self.assertEqual(self.c.productos.contar(), antes)     # ninguno llegó a la base

    def test_reponer_con_cantidad_invalida(self):
        self.entrar_admin()
        agua = self.producto("Agua embotellada")
        for cantidad in ("", "-10", "abc", "0"):
            with self.subTest(cantidad=cantidad):
                self.post(f"/admin/productos/{agua.id}/reponer", {"cantidad": cantidad}, pagina="/admin/")
                self.assertEqual(self.producto("Agua embotellada").existencias, agua.existencias)

    def test_registro_con_correo_mal_escrito(self):
        from modelos import Usuario
        datos = {"nombre": "Ana López", "correo": "ana-arroba-correo", "contrasena": "Clave1234",
                 "confirmacion": "Clave1234", "pregunta": Usuario.PREGUNTAS_SEGURIDAD[0],
                 "respuesta": "Firulais"}
        r = self.post("/registro", datos, pagina="/registro")
        self.assertIn("Escribe un correo válido", r.get_data(as_text=True))
        self.assertEqual(self.c.usuarios.contar(), 2)

    def test_cantidad_negativa_en_el_carrito(self):
        self.entrar_estudiante()
        agua = self.producto("Agua embotellada")
        for cantidad in ("-5", "0", "abc"):
            with self.subTest(cantidad=cantidad):
                r = self.post(f"/carrito/agregar/{agua.id}", {"cantidad": cantidad},
                              pagina="/tienda", follow_redirects=True)
                self.assertEqual(r.status_code, 200)
        self.assertIn("Tu carrito está vacío", self.cliente.get("/carrito").get_data(as_text=True))


# ======================================================================
# 3. Contraseñas y errores
# ======================================================================
class PruebasContrasenasYErrores(BaseSitio):

    def test_la_base_solo_guarda_hashes(self):
        with self.c.base_datos.conexion() as con:
            fila = con.execute("SELECT password_hash, respuesta_hash FROM usuarios "
                               "WHERE correo = 'estudiante@kiuvo.com'").fetchone()
        self.assertNotIn("Estudiante2026", fila["password_hash"])
        self.assertNotIn("pupusas", fila["respuesta_hash"])
        self.assertTrue(fila["password_hash"].startswith(("scrypt:", "pbkdf2:")))

    def test_el_usuario_nunca_ve_un_traceback(self):
        self.app.testing = False                        # como en el sitio real
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        self.entrar_admin()
        with mock.patch.object(self.c.productos, "listar",
                               side_effect=RuntimeError("detalle interno secreto")), \
                self.assertLogs(self.app.logger, "ERROR"):     # el detalle queda en el registro del servidor
            r = self.cliente.get("/admin/inventario")
        texto = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 500)
        self.assertIn("Algo salió mal", texto)
        self.assertNotIn("Traceback", texto)
        self.assertNotIn("detalle interno secreto", texto)
        self.assertNotIn(".py", texto)

    def test_paginas_inexistentes_y_debug_apagado(self):
        r = self.cliente.get("/no-existe")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn("Traceback", r.get_data(as_text=True))
        from config import Configuracion
        self.assertFalse(Configuracion.DEBUG)


if __name__ == "__main__":
    unittest.main()
