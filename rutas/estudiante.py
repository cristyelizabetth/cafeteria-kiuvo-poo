"""Páginas del estudiante: catálogos, carrito, pago y mis pedidos."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

import contenedor
import sesion
from modelos.excepciones import DatosInvalidos, ErrorCafeteria
from modelos.pago import MetodoPago
from modelos.producto import Almuerzo, ProductoTienda

bp = Blueprint("estudiante", __name__)


def _catalogo(clase_producto, titulo, subtitulo):
    """Misma página para almuerzos y tienda; cambia la clase de producto."""
    categoria = request.args.get("categoria")
    if categoria not in clase_producto.CATEGORIAS:
        categoria = None
    productos = contenedor.obtener().productos.listar(
        tipo=clase_producto.TIPO, categoria=categoria, solo_disponibles=True)
    return render_template("estudiante/catalogo.html", productos=productos,
                           categorias=clase_producto.CATEGORIAS,
                           categoria_actual=categoria, titulo=titulo, subtitulo=subtitulo)


@bp.route("/almuerzos")
@sesion.solo_compradores
def almuerzos():
    return _catalogo(Almuerzo, "Almuerzos", "Reserva tu almuerzo y recógelo en la cafetería.")


@bp.route("/tienda")
@sesion.solo_compradores
def tienda():
    return _catalogo(ProductoTienda, "Tienda", "Bebidas, snacks y postres disponibles hoy.")


@bp.route("/carrito")
@sesion.solo_compradores
def carrito():
    return render_template("estudiante/carrito.html", carrito=sesion.obtener_carrito())


def _leer_cantidad(valor_por_defecto=1):
    try:
        return int(request.form.get("cantidad", valor_por_defecto))
    except ValueError:
        raise DatosInvalidos("Escribe una cantidad válida.") from None


def _volver(por_defecto):
    destino = request.form.get("volver", "")
    if destino.startswith("/") and not destino.startswith("//"):
        return redirect(destino)
    return redirect(url_for(por_defecto))


@bp.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
@sesion.solo_compradores
def agregar(producto_id):
    producto = contenedor.obtener().productos.buscar_por_id(producto_id)
    if producto is None:
        flash("Ese producto no existe.", "error")
        return redirect(url_for("estudiante.almuerzos"))
    carrito = sesion.obtener_carrito()
    try:
        cantidad = _leer_cantidad()
        if cantidad < 1:
            raise DatosInvalidos("La cantidad debe ser al menos 1.")
        carrito.agregar(producto, cantidad)
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        sesion.guardar_carrito(carrito)
        verbo = "reservado" if producto.tipo == "almuerzo" else "agregado"
        flash(f"«{producto.nombre}» {verbo} en tu carrito.", "exito")
    return _volver("estudiante.carrito")


@bp.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
@sesion.solo_compradores
def actualizar(producto_id):
    producto = contenedor.obtener().productos.buscar_por_id(producto_id)
    carrito = sesion.obtener_carrito()
    if producto is not None:
        try:
            carrito.cambiar_cantidad(producto, _leer_cantidad())
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            sesion.guardar_carrito(carrito)
    return redirect(url_for("estudiante.carrito"))


@bp.route("/carrito/quitar/<int:producto_id>", methods=["POST"])
@sesion.solo_compradores
def quitar(producto_id):
    carrito = sesion.obtener_carrito()
    carrito.quitar(producto_id)
    sesion.guardar_carrito(carrito)
    flash("Producto quitado del carrito.", "exito")
    return redirect(url_for("estudiante.carrito"))


@bp.route("/pagar", methods=["GET", "POST"])
@sesion.solo_compradores
def pagar():
    carrito = sesion.obtener_carrito()
    if carrito.esta_vacio():
        flash("Tu carrito está vacío.", "aviso")
        return redirect(url_for("estudiante.almuerzos"))

    if request.method == "POST":
        try:
            pedido, mensaje = contenedor.obtener().servicio_pedidos.confirmar_compra(
                sesion.usuario_actual(), carrito, request.form.get("metodo"))
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            carrito.vaciar()
            sesion.guardar_carrito(carrito)
            flash(f"Pedido #{pedido.id}: {mensaje}", "exito")
            return redirect(url_for("estudiante.mis_pedidos"))
    return render_template("estudiante/pagar.html", carrito=carrito,
                           metodos=MetodoPago.disponibles())


@bp.route("/mis-pedidos")
@sesion.solo_compradores
def mis_pedidos():
    pedidos = contenedor.obtener().servicio_pedidos.pedidos_de(sesion.usuario_actual())
    nombres_pago = {m.CLAVE: m.nombre() for m in MetodoPago.disponibles()}
    return render_template("estudiante/mis_pedidos.html", pedidos=pedidos,
                           nombres_pago=nombres_pago)


@bp.route("/mis-pedidos/<int:pedido_id>/cancelar", methods=["POST"])
@sesion.solo_compradores
def cancelar(pedido_id):
    try:
        contenedor.obtener().servicio_pedidos.cancelar(sesion.usuario_actual(), pedido_id)
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        flash(f"Pedido #{pedido_id} cancelado. Los productos volvieron al inventario.", "exito")
    return redirect(url_for("estudiante.mis_pedidos"))
