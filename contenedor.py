"""Contenedor: guarda en un solo objeto los DAO y servicios de la aplicación.

app.py lo crea una vez; las rutas lo obtienen con obtener().
"""

from dataclasses import dataclass

from flask import current_app

from base_datos import BaseDatos
from dao import CategoriaDAO, PedidoDAO, ProductoDAO, UsuarioDAO
from seguridad import ProtectorCSRF
from servicios import ServicioAutenticacion, ServicioInventario, ServicioPedidos

CLAVE_EXTENSION = "kiuvo"


@dataclass
class Contenedor:
    base_datos: BaseDatos
    usuarios: UsuarioDAO
    categorias: CategoriaDAO
    productos: ProductoDAO
    pedidos: PedidoDAO
    autenticacion: ServicioAutenticacion
    servicio_pedidos: ServicioPedidos
    inventario: ServicioInventario
    csrf: ProtectorCSRF


def obtener():
    return current_app.extensions[CLAVE_EXTENSION]
