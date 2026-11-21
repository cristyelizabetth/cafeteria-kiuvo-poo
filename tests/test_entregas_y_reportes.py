"""Pruebas de las mejoras de la versión final (pedidas por la gerente de la cafetería):

- código de recibo y estados de entrega (entregado / no recogido);
- reporte mensual de ventas y productos por agotarse (consultas propias del negocio).

Ejecutar:   python -m unittest tests.test_entregas_y_reportes -v
"""

import re
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modelos import (Almuerzo, CambioEstadoInvalido, Carrito, DatosInvalidos,  # noqa: E402
                     ItemPedido, Pedido, PedidoNoCancelable, ProductoTienda,
                     RegistroDuplicado, ReporteMensual)
from modelos.pedido import EstadoPedido                                       # noqa: E402
from servicios import ServicioPedidos, ServicioReportes                       # noqa: E402
from tests.test_cafeteria import BaseSitio                                    # noqa: E402
from tests.test_dao import BaseMemoria                                        # noqa: E402

HOY = date.today()
MES_ACTUAL = f"{HOY.year:04d}-{HOY.month:02d}"


# ======================================================================
# 1. El modelo: código de recibo y cambios de estado
# ======================================================================
class PruebasModeloPedido(unittest.TestCase):

    def pedido(self):
        return Pedido(1, [ItemPedido(1, "Agua", 0.75, 2)], "caja")

    def test_cada_pedido_recibe_un_codigo_distinto(self):
        codigos = {self.pedido().codigo for _ in range(200)}
        self.assertEqual(len(codigos), 200)
        for codigo in codigos:
            self.assertRegex(codigo, r"^KV-[A-HJ-NP-Z2-9]{6}$")   # sin 0, O, 1, I ni L

    def test_el_codigo_se_escribe_de_varias_formas(self):
        for escrito in ("kv-7f3k9q", " KV-7F3K9Q ", "7f3k9q", "KV7F3K9Q"):
            with self.subTest(escrito=escrito):
                self.assertEqual(Pedido.normalizar_codigo(escrito), "KV-7F3K9Q")
        for malo in ("", "KV-123", "KV-7F3K9Q9", "' OR '1'='1"):
            with self.subTest(malo=malo), self.assertRaises(DatosInvalidos):
                Pedido.normalizar_codigo(malo)

    def test_pendiente_pasa_a_entregado_o_no_recogido(self):
        entregado, olvidado = self.pedido(), self.pedido()
        entregado.marcar_entregado()
        olvidado.marcar_no_recogido()
        self.assertEqual(entregado.estado, EstadoPedido.ENTREGADO)
        self.assertEqual(olvidado.estado, EstadoPedido.NO_RECOGIDO)

    def test_un_pedido_cerrado_ya_no_cambia(self):
        entregado = self.pedido()
        entregado.marcar_entregado()
        with self.assertRaises(CambioEstadoInvalido):
            entregado.marcar_no_recogido()
        with self.assertRaises(PedidoNoCancelable):
            entregado.cancelar()                        # ya se lo llevó: no se puede cancelar
        cancelado = self.pedido()
        cancelado.cancelar()
        with self.assertRaises(CambioEstadoInvalido):
            cancelado.marcar_entregado()


# ======================================================================
# 2. La capa DAO: código único, búsqueda y consultas propias
# ======================================================================
class PruebasDAOEntregasYReportes(BaseMemoria):

    def comprar(self, nombre, cantidad, fecha=None):
        p = self.producto(nombre)
        pedido = Pedido(self.alumno.id, [ItemPedido(p.id, p.nombre, p.precio, cantidad)], "caja",
                        fecha=fecha)
        return self.pedidos.insertar(pedido)

    def test_buscar_por_codigo(self):
        pedido = self.comprar("Agua embotellada", 1)
        encontrado = self.pedidos.buscar_por_codigo(pedido.codigo)
        self.assertEqual((encontrado.id, encontrado.codigo), (pedido.id, pedido.codigo))
        self.assertIsNone(self.pedidos.buscar_por_codigo("KV-ZZZZZZ"))

    def test_la_base_no_acepta_dos_pedidos_con_el_mismo_codigo(self):
        primero = self.comprar("Agua embotellada", 1)
        agua = self.producto("Agua embotellada")
        antes = agua.existencias
        repetido = Pedido(self.alumno.id, [ItemPedido(agua.id, agua.nombre, agua.precio, 1)], "caja",
                          codigo=primero.codigo)
        with self.assertRaises(RegistroDuplicado):
            self.pedidos.insertar(repetido)
        self.assertEqual(self.producto("Agua embotellada").existencias, antes)   # rollback

    def test_si_el_codigo_ya_existia_se_sortea_otro(self):
        primero = self.comprar("Agua embotellada", 1)
        otro = "KV-ABCDEF"
        carrito = Carrito()
        carrito.agregar(self.producto("Brownie"), 1)
        with mock.patch.object(Pedido, "generar_codigo", side_effect=[primero.codigo, otro]):
            pedido, _ = ServicioPedidos(self.productos, self.pedidos).confirmar_compra(
                self.alumno, carrito, "caja")
        self.assertEqual(pedido.codigo, otro)
        self.assertEqual(self.pedidos.contar(), 2)

    def test_marcar_entregado_se_guarda(self):
        pedido = self.comprar("Agua embotellada", 1)
        servicio = ServicioPedidos(self.productos, self.pedidos)
        servicio.marcar_entregado(pedido.id)
        self.assertEqual(self.pedidos.buscar_por_id(pedido.id).estado, EstadoPedido.ENTREGADO)
        with self.assertRaises(CambioEstadoInvalido):
            servicio.marcar_no_recogido(pedido.id)

    def test_no_recogido_no_devuelve_el_inventario(self):
        """La comida ya se preparó: si no la recogen, no vuelve al inventario."""
        pedido = self.comprar("Agua embotellada", 2)
        despues_de_comprar = self.producto("Agua embotellada").existencias
        ServicioPedidos(self.productos, self.pedidos).marcar_no_recogido(pedido.id)
        self.assertEqual(self.producto("Agua embotellada").existencias, despues_de_comprar)

    def test_reporte_mensual_suma_por_producto(self):
        agua, brownie = self.producto("Agua embotellada"), self.producto("Brownie")
        self.comprar("Agua embotellada", 2)
        self.comprar("Agua embotellada", 3)
        self.comprar("Brownie", 1)
        cancelado = self.comprar("Brownie", 4)
        cancelado.cancelar()
        self.pedidos.cancelar(cancelado)
        olvidado = self.comprar("Agua embotellada", 1)
        olvidado.marcar_no_recogido()
        self.pedidos.actualizar(olvidado)
        self.comprar("Brownie", 7, fecha="2020-01-15 12:00")       # otro mes: no cuenta

        reporte = self.pedidos.reporte_mensual(HOY.year, HOY.month)
        self.assertIsInstance(reporte, ReporteMensual)               # devuelve un objeto
        por_producto = {linea.producto: (linea.unidades, linea.total) for linea in reporte.lineas}
        self.assertEqual(por_producto, {
            "Agua embotellada": (6, round(6 * agua.precio, 2)),        # 2 + 3 + 1 no recogido
            "Brownie": (1, round(1 * brownie.precio, 2)),             # el cancelado no cuenta
        })
        self.assertEqual(reporte.lineas[0].producto, "Agua embotellada")   # ordenado por total
        self.assertEqual(reporte.total_vendido, round(6 * agua.precio + brownie.precio, 2))
        self.assertEqual((reporte.pedidos("pendiente"), reporte.pedidos("no_recogido"),
                          reporte.pedidos("cancelado")), (3, 1, 1))
        self.assertEqual(reporte.total_pedidos, 4)

    def test_reporte_de_un_mes_sin_ventas(self):
        reporte = self.pedidos.reporte_mensual(2021, 2)
        self.assertTrue(reporte.esta_vacio)
        self.assertEqual((reporte.total_vendido, reporte.nombre), (0, "Febrero 2021"))

    def test_mes_invalido(self):
        for anio, mes in ((2026, 13), (2026, 0), ("abc", 5), (1990, 5)):
            with self.subTest(anio=anio, mes=mes), self.assertRaises(DatosInvalidos):
                self.pedidos.reporte_mensual(anio, mes)
        for texto in ("", "noviembre", "2026/11", "2026-13"):
            with self.subTest(texto=texto), self.assertRaises(DatosInvalidos):
                ServicioReportes(self.pedidos, self.productos).reporte(texto or "x")

    def test_el_reporte_se_exporta_para_excel(self):
        self.comprar("Agua embotellada", 2)
        csv = self.pedidos.reporte_mensual(HOY.year, HOY.month).a_csv()
        self.assertTrue(csv.startswith("﻿"))              # Excel lee bien las tildes
        self.assertIn("Agua embotellada,Producto de tienda,2,", csv)
        self.assertIn("TOTAL", csv)

    def test_existencias_bajas_con_el_limite_de_cada_clase(self):
        # Almuerzo: límite 5 · Producto de tienda: límite 10
        self.productos.insertar(Almuerzo("Sopa del día", "", "Plato del día", 2, 5))
        self.productos.insertar(Almuerzo("Arroz con pollo", "", "Plato del día", 2, 6))
        self.productos.insertar(ProductoTienda("Galletas", "", "Snacks", 1, 10))
        oculto = self.productos.insertar(ProductoTienda("Té frío", "", "Bebidas", 1, 0))
        oculto.desactivar()
        self.productos.actualizar(oculto)

        bajos = self.productos.listar_existencias_bajas()
        nombres = [p.nombre for p in bajos]
        self.assertIn("Sopa del día", nombres)             # 5 ≤ 5
        self.assertNotIn("Arroz con pollo", nombres)       # 6 > 5
        self.assertIn("Galletas", nombres)                 # 10 ≤ 10
        self.assertNotIn("Té frío", nombres)               # oculto: no se avisa
        existencias = [p.existencias for p in bajos]
        self.assertEqual(existencias, sorted(existencias))  # de menos a más


# ======================================================================
# 3. El sitio: recibo, entrega en la barra y página de reportes
# ======================================================================
class PruebasSitioEntregasYReportes(BaseSitio):

    def comprar_agua(self, cantidad=1):
        self.entrar_estudiante()
        agua = self.producto("Agua embotellada")
        self.post(f"/carrito/agregar/{agua.id}", {"cantidad": cantidad}, pagina="/tienda")
        return self.post("/pagar", {"metodo": "caja"}, pagina="/pagar", follow_redirects=True)

    def test_al_pagar_se_ve_el_recibo_con_su_codigo(self):
        html = self.comprar_agua().get_data(as_text=True)
        pedido = self.c.pedidos.listar()[0]
        self.assertIn("La cafetería ya recibió tu pedido", html)
        self.assertIn(pedido.codigo, html)
        self.assertIn(pedido.codigo, self.cliente.get("/mis-pedidos").get_data(as_text=True))

    def test_nadie_ve_el_recibo_de_otra_persona(self):
        self.comprar_agua()
        pedido = self.c.pedidos.listar()[0]
        self.post("/logout", pagina="/")
        from modelos import Usuario
        self.post("/registro", {"nombre": "Otra Persona", "correo": "otra@kiuvo.com",
                                "contrasena": "Clave1234", "confirmacion": "Clave1234",
                                "pregunta": Usuario.PREGUNTAS_SEGURIDAD[0], "respuesta": "x y"},
                  pagina="/registro")
        self.assertEqual(self.cliente.get(f"/mis-pedidos/{pedido.id}").status_code, 404)
        self.assertEqual(self.cliente.get("/mis-pedidos/99999").status_code, 404)

    def test_la_cafeteria_busca_el_codigo_y_entrega(self):
        self.comprar_agua()
        pedido = self.c.pedidos.listar()[0]
        self.post("/logout", pagina="/")
        self.entrar_admin()
        escrito = pedido.codigo.lower().removeprefix("kv-")        # como lo dicte el estudiante
        html = self.cliente.get(f"/admin/pedidos?codigo={escrito}").get_data(as_text=True)
        self.assertIn("pedido--encontrado", html)
        self.assertIn(pedido.codigo, html)

        r = self.post(f"/admin/pedidos/{pedido.id}/entregado", pagina="/admin/", follow_redirects=True)
        self.assertIn("entregado", r.get_data(as_text=True))
        self.assertEqual(self.c.pedidos.buscar_por_id(pedido.id).estado, EstadoPedido.ENTREGADO)
        # entregar dos veces no se puede
        r = self.post(f"/admin/pedidos/{pedido.id}/entregado", pagina="/admin/", follow_redirects=True)
        self.assertIn("ya está «entregado»", r.get_data(as_text=True))

    def test_codigo_mal_escrito_o_inexistente(self):
        self.entrar_admin()
        html = self.cliente.get("/admin/pedidos?codigo=hola").get_data(as_text=True)
        self.assertIn("El código no es válido", html)
        html = self.cliente.get("/admin/pedidos?codigo=KV-ZZZZZZ").get_data(as_text=True)
        self.assertIn("No hay ningún pedido con el código KV-ZZZZZZ", html)

    def test_el_estudiante_no_cancela_lo_ya_entregado(self):
        self.comprar_agua()
        pedido = self.c.pedidos.listar()[0]
        self.c.servicio_pedidos.marcar_entregado(pedido.id)
        r = self.post(f"/mis-pedidos/{pedido.id}/cancelar", pagina="/mis-pedidos", follow_redirects=True)
        self.assertIn("ya no se puede cancelar", r.get_data(as_text=True))

    def test_pagina_de_reportes_y_descarga(self):
        self.comprar_agua(3)
        self.post("/logout", pagina="/")
        self.entrar_admin()
        html = self.cliente.get(f"/admin/reportes?mes={MES_ACTUAL}").get_data(as_text=True)
        self.assertIn("Agua embotellada", html)
        self.assertIn("Total vendido", html)
        r = self.cliente.get(f"/admin/reportes/descargar?mes={MES_ACTUAL}")
        self.assertEqual(r.mimetype, "text/csv")
        self.assertIn(f"reporte-ventas-{MES_ACTUAL}.csv", r.headers["Content-Disposition"])
        self.assertIn("Agua embotellada", r.get_data(as_text=True))
        r.close()

    def test_reporte_con_mes_invalido_muestra_mensaje(self):
        self.entrar_admin()
        r = self.cliente.get("/admin/reportes?mes=2026-13")
        self.assertEqual(r.status_code, 200)                  # no se cae: vuelve al mes actual
        self.assertIn("El mes debe estar entre 1 y 12", r.get_data(as_text=True))

    def test_solo_el_admin_ve_reportes_y_entrega(self):
        self.entrar_estudiante()
        self.assertEqual(self.cliente.get("/admin/reportes").status_code, 403)
        self.assertEqual(self.post("/admin/pedidos/1/entregado", pagina="/tienda").status_code, 403)

    def test_el_panel_avisa_lo_que_se_esta_agotando(self):
        agua = self.producto("Agua embotellada")
        agua.existencias = 2
        self.c.productos.actualizar(agua)
        self.entrar_admin()
        html = self.cliente.get("/admin/").get_data(as_text=True)
        seccion = html.split("Necesitan atención", 1)[1]
        self.assertTrue(re.search(r"Agua embotellada", seccion))


if __name__ == "__main__":
    unittest.main()
