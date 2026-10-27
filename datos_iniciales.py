"""Datos de ejemplo que se cargan la primera vez que se crea la base de datos."""

import os

from modelos.producto import Almuerzo, Producto, ProductoTienda
from modelos.usuario import Administrador, Estudiante

ALMUERZOS = [
    ("Pollo guisado", "Pollo en salsa de tomate con especias.", "Plato del día", 3.50,
     30, "Arroz, ensalada y fresco"),
    ("Carne asada", "Carne de res a la plancha.", "Plato del día", 4.25,
     25, "Arroz, frijoles, tortillas y fresco"),
    ("Pupusas revueltas (3)", "Tres pupusas de chicharrón con queso.", "Plato del día", 2.75,
     40, "Curtido y salsa"),
    ("Lasaña de vegetales", "Capas de pasta con espinaca, calabacín y queso.", "Vegetariano",
     3.75, 15, "Pan con ajo y fresco"),
    ("Ensalada César con pollo", "Lechuga, pollo, crutones y aderezo César.", "Ligero",
     3.25, 4, "Fresco natural"),
    ("Wrap integral de pollo", "Tortilla integral con pollo y vegetales.", "Ligero",
     3.00, 0, "Fruta picada"),
]

PRODUCTOS_TIENDA = [
    ("Agua embotellada", "Agua purificada.", "Bebidas", 0.75, 48, "Botella 600 ml"),
    ("Café americano", "Café de altura salvadoreño.", "Bebidas", 1.00, 60, "Vaso 12 oz"),
    ("Jugo de naranja", "Jugo natural.", "Bebidas", 1.25, 20, "Botella 350 ml"),
    ("Galletas de avena", "Galletas caseras.", "Snacks", 0.90, 35, "Paquete de 6"),
    ("Chips de plátano", "Plátano frito con sal.", "Snacks", 0.80, 8, "Bolsa 50 g"),
    ("Brownie", "Brownie de chocolate.", "Postres", 1.50, 12, "Porción individual"),
    ("Quesadilla salvadoreña", "Pan dulce de queso.", "Postres", 1.25, 0, "Porción"),
]


def cargar_datos_iniciales(usuario_dao, categoria_dao, producto_dao):
    """Solo carga datos si las tablas están vacías; no duplica nada."""
    # Las categorías se aseguran siempre (INSERT OR IGNORE no repite las que ya están).
    categoria_dao.asegurar(Producto.tipos())

    if usuario_dao.contar(rol=Administrador.ROL) == 0:
        usuario_dao.insertar(Administrador.crear(
            nombre="Administración Kiuvo",
            correo="admin@kiuvo.com",
            contrasena=os.environ.get("KIUVO_ADMIN_PASSWORD", "Kiuvo2026"),
            pregunta="¿Cuál es tu comida favorita?",
            respuesta="pupusas",
        ))
        usuario_dao.insertar(Estudiante.crear(
            nombre="Estudiante de Prueba",
            correo="estudiante@kiuvo.com",
            contrasena="Estudiante2026",
            pregunta="¿Cuál es tu comida favorita?",
            respuesta="pupusas",
        ))

    if producto_dao.contar() == 0:
        for nombre, desc, cat, precio, exist, incluye in ALMUERZOS:
            producto_dao.insertar(Almuerzo(nombre, desc, cat, precio, exist, incluye=incluye))
        for nombre, desc, cat, precio, exist, presentacion in PRODUCTOS_TIENDA:
            producto_dao.insertar(ProductoTienda(nombre, desc, cat, precio, exist,
                                                  presentacion=presentacion))
