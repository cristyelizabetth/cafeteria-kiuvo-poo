"""Capa DAO (acceso a datos): la única parte del programa que habla con SQLite.

    DAO (clase abstracta = interfaz)
     ├── UsuarioDAO     → tabla usuarios
     ├── CategoriaDAO   → tabla categorias
     ├── ProductoDAO    → tablas productos, almuerzos y productos_tienda
     └── PedidoDAO      → tablas pedidos y detalle_pedido
"""

from dao.base import DAO
from dao.categoria_dao import CategoriaDAO
from dao.pedido_dao import PedidoDAO
from dao.producto_dao import ProductoDAO
from dao.usuario_dao import UsuarioDAO
