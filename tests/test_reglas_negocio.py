"""Pruebas de las reglas del negocio (capa de servicios), con base ":memory:".

Ejecutar:   python -m unittest tests.test_reglas_negocio -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imagenes import GestorImagenes                                    # noqa: E402
from modelos import (Carrito, DatosInvalidos, ErrorCafeteria,          # noqa: E402
                     InventarioInsuficiente, PedidoNoCancelable, RegistroDuplicado)
from modelos.pedido import EstadoPedido                                # noqa: E402
from servicios import ServicioInventario, ServicioPedidos              # noqa: E402
from tests.test_dao import BaseMemoria                                 # noqa: E402


class PruebasReglasNegocio(BaseMemoria):

    def setUp(self):
        super().setUp()
        self.servicio = ServicioPedidos(self.productos, self.pedidos)
        self.admin = self.usuarios.buscar_por_correo("admin@kiuvo.com")

    def carrito_con(self, nombre, cantidad):
        carrito = Carrito()
        carrito.agregar(self.producto(nombre), cantidad)
        return carrito

    # Regla 1
    def test_comprar_descuenta_el_inventario(self):
        antes = self.producto("Agua embotellada").existencias
        pedido, _ = self.servicio.confirmar_compra(self.alumno, self.carrito_con("Agua embotellada", 3), "caja")
        self.assertEqual(self.producto("Agua embotellada").existencias, antes - 3)
        self.assertEqual(pedido.estado, EstadoPedido.PENDIENTE)

    # Regla 2
    def test_no_se_vende_mas_de_lo_que_hay_y_no_queda_nada_a_medias(self):
        carrito = self.carrito_con("Agua embotellada", 2)
        carrito.agregar(self.producto("Brownie"), 1)
        # mientras tanto, otra estudiante se llevó casi todo el agua
        agua = self.producto("Agua embotellada")
        agua.existencias = 1
        self.productos.actualizar(agua)
        brownies_antes = self.producto("Brownie").existencias

        with self.assertRaises(InventarioInsuficiente):
            self.servicio.confirmar_compra(self.alumno, carrito, "caja")
        self.assertEqual(self.pedidos.contar(), 0)                              # no se creó el pedido
        self.assertEqual(self.producto("Agua embotellada").existencias, 1)      # nada negativo
        self.assertEqual(self.producto("Brownie").existencias, brownies_antes)  # rollback completo

    # Regla 3
    def test_cancelar_devuelve_el_inventario_y_solo_una_vez(self):
        antes = self.producto("Agua embotellada").existencias
        pedido, _ = self.servicio.confirmar_compra(self.alumno, self.carrito_con("Agua embotellada", 2), "caja")
        self.servicio.cancelar(self.alumno, pedido.id)
        self.assertEqual(self.producto("Agua embotellada").existencias, antes)
        with self.assertRaises(PedidoNoCancelable):
            self.servicio.cancelar(self.alumno, pedido.id)                       # ya estaba cancelado

    # Regla 4
    def test_el_administrador_no_puede_comprar(self):
        with self.assertRaises(ErrorCafeteria):
            self.servicio.confirmar_compra(self.admin, self.carrito_con("Agua embotellada", 1), "caja")

    # Regla 5
    def test_carrito_vacio_o_metodo_de_pago_invalido(self):
        with self.assertRaises(DatosInvalidos):
            self.servicio.confirmar_compra(self.alumno, Carrito(), "caja")
        with self.assertRaises(DatosInvalidos):
            self.servicio.confirmar_compra(self.alumno, self.carrito_con("Agua embotellada", 1), "bitcoin")

    # Regla 6
    def test_no_se_repiten_nombres_de_productos(self):
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            inventario = ServicioInventario(self.productos, GestorImagenes(carpeta))
            with self.assertRaises(RegistroDuplicado):
                inventario.crear("tienda", {"nombre": " BROWNIE ", "categoria": "Postres",
                                            "precio": "1", "existencias": "1"})


if __name__ == "__main__":
    unittest.main()
