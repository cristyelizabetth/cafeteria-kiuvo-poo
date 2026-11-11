"""Pruebas de la capa DAO y de la persistencia.

Todas usan una base de datos en memoria (":memory:"): cada prueba empieza
con una base nueva y vacía, y no deja archivos. La única excepción es la
prueba de persistencia, que necesita un archivo real para cerrarlo y reabrirlo.

Ejecutar todas las pruebas:   python -m unittest -v
Solo este archivo:            python -m unittest tests.test_dao -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base_datos import BaseDatos                                      # noqa: E402
from dao import DAO, CategoriaDAO, PedidoDAO, ProductoDAO, UsuarioDAO   # noqa: E402
from datos_iniciales import cargar_datos_iniciales                    # noqa: E402
from modelos import (Almuerzo, Categoria, DatosInvalidos, Estudiante,  # noqa: E402
                     ItemPedido, Pedido, ProductoTienda, ReferenciaInvalida,
                     RegistroDuplicado, RegistroEnUso, RegistroNoEncontrado)
from modelos.pedido import EstadoPedido                               # noqa: E402


class BaseMemoria(unittest.TestCase):
    """Crea una base en memoria con los datos de ejemplo y los cuatro DAO."""

    def setUp(self):
        self.bd = BaseDatos(":memory:")
        self.bd.inicializar()
        self.usuarios = UsuarioDAO(self.bd)
        self.categorias = CategoriaDAO(self.bd)
        self.productos = ProductoDAO(self.bd)
        self.pedidos = PedidoDAO(self.bd)
        cargar_datos_iniciales(self.usuarios, self.categorias, self.productos)
        self.alumno = self.usuarios.buscar_por_correo("estudiante@kiuvo.com")

    def tearDown(self):
        self.bd.cerrar()

    def producto(self, nombre):
        return next(p for p in self.productos.listar() if p.nombre == nombre)


# ======================================================================
# CRUD completo de cada DAO (crear, leer, listar, actualizar, eliminar)
# ======================================================================
class PruebasCRUD(BaseMemoria):

    def test_todos_los_dao_cumplen_la_interfaz(self):
        with self.assertRaises(TypeError):
            DAO(self.bd)                              # la interfaz no se puede instanciar
        for dao in (self.usuarios, self.categorias, self.productos, self.pedidos):
            self.assertIsInstance(dao, DAO)

    def test_crud_usuario_dao(self):
        nuevo = Estudiante.crear("Ana López", "ana@kiuvo.com", "Clave1234", "p", "r")
        self.usuarios.insertar(nuevo)                                          # C
        self.assertIsNotNone(nuevo.id)
        leido = self.usuarios.buscar_por_id(nuevo.id)                          # R
        self.assertIsInstance(leido, Estudiante)                               # devuelve objetos
        self.assertEqual(leido.correo, "ana@kiuvo.com")
        self.assertIn("ana@kiuvo.com", [u.correo for u in self.usuarios.listar()])
        leido.cambiar_contrasena("NuevaClave99")
        self.usuarios.actualizar(leido)                                        # U
        self.assertTrue(self.usuarios.buscar_por_id(nuevo.id).verificar_contrasena("NuevaClave99"))
        self.usuarios.eliminar(nuevo.id)                                       # D
        self.assertIsNone(self.usuarios.buscar_por_id(nuevo.id))

    def test_crud_categoria_dao(self):
        cat = self.categorias.insertar(Categoria("Desayunos", "almuerzo"))     # C
        leida = self.categorias.buscar_por_id(cat.id)                          # R
        self.assertIsInstance(leida, Categoria)
        self.assertIn("Desayunos", [c.nombre for c in self.categorias.listar(tipo="almuerzo")])
        leida.nombre = "Desayunos típicos"
        self.categorias.actualizar(leida)                                      # U
        self.assertEqual(self.categorias.buscar_por_id(cat.id).nombre, "Desayunos típicos")
        self.categorias.eliminar(cat.id)                                       # D
        self.assertIsNone(self.categorias.buscar_por_id(cat.id))

    def test_crud_producto_dao(self):
        nuevo = self.productos.insertar(
            Almuerzo("Sopa de frijoles", "Con huevo", "Plato del día", 2.5, 20, incluye="Tortillas"))
        leido = self.productos.buscar_por_id(nuevo.id)                         # R
        self.assertIsInstance(leido, Almuerzo)                                 # objeto de la clase hija
        self.assertEqual(leido.incluye, "Tortillas")
        self.assertIn(nuevo.id, [p.id for p in self.productos.listar(tipo="almuerzo")])
        leido.precio = 2.75
        leido.incluye = "Tortillas y fresco"
        self.productos.actualizar(leido)                                       # U
        otra_vez = self.productos.buscar_por_id(nuevo.id)
        self.assertEqual((otra_vez.precio, otra_vez.incluye), (2.75, "Tortillas y fresco"))
        self.productos.eliminar(nuevo.id)                                      # D
        self.assertIsNone(self.productos.buscar_por_id(nuevo.id))

    def test_crud_pedido_dao(self):
        agua = self.producto("Agua embotellada")
        pedido = Pedido(self.alumno.id, [ItemPedido(agua.id, agua.nombre, agua.precio, 2)], "caja")
        self.pedidos.insertar(pedido)                                          # C
        leido = self.pedidos.buscar_por_id(pedido.id)                          # R
        self.assertIsInstance(leido, Pedido)
        self.assertEqual((leido.total, leido.items[0].cantidad), (round(agua.precio * 2, 2), 2))
        self.assertEqual([p.id for p in self.pedidos.listar(usuario_id=self.alumno.id)], [pedido.id])
        leido.cancelar()
        self.pedidos.actualizar(leido)                                         # U
        self.assertEqual(self.pedidos.buscar_por_id(pedido.id).estado, EstadoPedido.CANCELADO)
        self.pedidos.eliminar(pedido.id)                                       # D
        self.assertIsNone(self.pedidos.buscar_por_id(pedido.id))


# ======================================================================
# Casos borde: id inexistente, datos inválidos, llave foránea inválida
# ======================================================================
class PruebasCasosBorde(BaseMemoria):

    def test_id_inexistente(self):
        for dao in (self.usuarios, self.categorias, self.productos, self.pedidos):
            self.assertIsNone(dao.buscar_por_id(99999))           # buscar: devuelve None
            with self.assertRaises(RegistroNoEncontrado):
                dao.eliminar(99999)                                # borrar: avisa que no existe
        fantasma = ProductoTienda("Fantasma", "", "Bebidas", 1, 1, id=99999)
        with self.assertRaises(RegistroNoEncontrado):
            self.productos.actualizar(fantasma)                   # actualizar: avisa que no existe

    def test_datos_invalidos_se_rechazan_antes_de_la_base(self):
        casos = [
            lambda: ProductoTienda("", "", "Bebidas", 1, 1),             # nombre vacío
            lambda: ProductoTienda("Jugo", "", "Bebidas", -1, 1),        # precio negativo
            lambda: ProductoTienda("Jugo", "", "Bebidas", "abc", 1),     # precio con formato malo
            lambda: ProductoTienda("Jugo", "", "Bebidas", 1, -5),        # existencias negativas
            lambda: ProductoTienda("Jugo", "", "Bebidas", 1, 2.5),       # existencias con decimales
            lambda: ProductoTienda("Jugo", "", "Plato del día", 1, 1),   # categoría de otro tipo
            lambda: ItemPedido(1, "Agua", 0.75, 0),                      # cantidad 0
            lambda: ItemPedido(1, "Agua", -1, 1),                        # precio negativo
            lambda: Pedido(self.alumno.id, [], "caja"),                  # pedido sin productos
        ]
        antes = self.productos.contar()
        for crear in casos:
            with self.subTest():
                with self.assertRaises(DatosInvalidos):
                    crear()
        self.assertEqual(self.productos.contar(), antes)          # no llegó nada a la base

    def test_la_base_tambien_rechaza_datos_invalidos(self):
        """Segunda barrera: aunque alguien se salte Python, las reglas CHECK de SQLite lo frenan."""
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with self.bd.conexion() as con:
                con.execute("UPDATE productos SET precio = -5 WHERE id = 1")
        self.assertGreaterEqual(self.productos.buscar_por_id(1).precio, 0)

    def test_llave_foranea_invalida(self):
        agua = self.producto("Agua embotellada")
        # pedido de un estudiante que no existe
        with self.assertRaises(ReferenciaInvalida):
            self.pedidos.insertar(Pedido(99999, [ItemPedido(agua.id, agua.nombre, 0.75, 1)], "caja"))
        # producto con una categoría que no existe
        with self.assertRaises(DatosInvalidos):
            self.productos.insertar(ProductoTienda("Té frío", "", "Inventada", 1, 1))
        # y directo en SQL: la base no acepta una categoria_id que no existe
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            with self.bd.conexion() as con:
                con.execute("INSERT INTO productos (tipo, nombre, categoria_id, precio, existencias) "
                            "VALUES ('tienda', 'X', 99999, 1, 1)")
        self.assertEqual(self.pedidos.contar(), 0)                # no quedó nada a medias

    def test_borrar_algo_que_otros_usan(self):
        agua = self.producto("Agua embotellada")
        self.pedidos.insertar(Pedido(self.alumno.id, [ItemPedido(agua.id, agua.nombre, 0.75, 1)], "caja"))
        with self.assertRaises(RegistroEnUso):
            self.productos.eliminar(agua.id)                      # ya aparece en un pedido
        with self.assertRaises(RegistroEnUso):
            self.usuarios.eliminar(self.alumno.id)                # tiene pedidos

    def test_duplicados(self):
        with self.assertRaises(RegistroDuplicado):
            self.usuarios.insertar(Estudiante.crear("Otra", "ESTUDIANTE@kiuvo.com", "Clave1234", "p", "r"))
        with self.assertRaises(RegistroDuplicado):
            self.productos.insertar(ProductoTienda("agua EMBOTELLADA", "", "Bebidas", 1, 1))


# ======================================================================
# Persistencia: los datos siguen ahí al cerrar y volver a abrir
# ======================================================================
class PruebasPersistencia(unittest.TestCase):

    def test_datos_siguen_al_cerrar_y_reabrir(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "kiuvo.db")
            primera = BaseDatos(ruta)
            primera.inicializar()
            CategoriaDAO(primera).asegurar((ProductoTienda,))
            nuevo = ProductoDAO(primera).insertar(ProductoTienda("Horchata", "", "Bebidas", 1, 10))
            del primera                                             # "cerramos" el programa

            segunda = BaseDatos(ruta)                               # lo volvemos a abrir
            segunda.inicializar()
            leido = ProductoDAO(segunda).buscar_por_id(nuevo.id)
            self.assertEqual((leido.nombre, leido.existencias), ("Horchata", 10))

    def test_llaves_foraneas_activadas(self):
        bd = BaseDatos(":memory:")
        with bd.conexion() as con:
            self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        bd.cerrar()

    def test_transaccion_todo_o_nada(self):
        bd = BaseDatos(":memory:")
        bd.inicializar()
        CategoriaDAO(bd).asegurar((ProductoTienda,))
        with self.assertRaises(RuntimeError):
            with bd.conexion() as con:
                con.execute("INSERT INTO categorias (nombre, tipo) VALUES ('Temporal', 'tienda')")
                raise RuntimeError("falla a medio camino")
        nombres = [c.nombre for c in CategoriaDAO(bd).listar()]
        self.assertNotIn("Temporal", nombres)                     # se deshizo (rollback)
        bd.cerrar()


if __name__ == "__main__":
    unittest.main()
