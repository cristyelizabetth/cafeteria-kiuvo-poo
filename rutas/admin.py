"""Páginas del administrador: panel, inventario, productos y pedidos."""

from flask import (Blueprint, Response, abort, flash, redirect, render_template, request,
                   url_for)

import contenedor
import sesion
from modelos.excepciones import ErrorCafeteria
from modelos.pago import MetodoPago
from modelos.pedido import EstadoPedido
from modelos.producto import Almuerzo, Producto, ProductoTienda

bp = Blueprint("admin", __name__, url_prefix="/admin")

TIPOS = {Almuerzo.TIPO: Almuerzo, ProductoTienda.TIPO: ProductoTienda}


def _regresar():
    """Vuelve a la página anterior solo si es de este mismo sitio."""
    anterior = request.referrer or ""
    if anterior.startswith(request.host_url):
        return redirect(anterior)
    return redirect(url_for("admin.inventario"))


@bp.route("/")
@sesion.solo_administradores
def panel():
    c = contenedor.obtener()
    productos = c.productos.listar()
    resumen = {
        "productos": len(productos),
        "agotados": sum(1 for p in productos if p.activo and p.existencias == 0),
        "bajos": sum(1 for p in productos if p.activo and p.existencias_bajas()),
        "pendientes": c.pedidos.contar(EstadoPedido.PENDIENTE.value),
        "estudiantes": c.usuarios.contar("estudiante"),
    }
    alertas = c.reportes.existencias_bajas()        # consulta propia (SQL en ProductoDAO)
    return render_template("admin/panel.html", resumen=resumen, alertas=alertas)


@bp.route("/inventario")
@sesion.solo_administradores
def inventario():
    tipo = request.args.get("tipo")
    if tipo not in TIPOS:
        tipo = None
    categoria = request.args.get("categoria")
    categorias = TIPOS[tipo].CATEGORIAS if tipo else ()
    if categoria not in categorias:
        categoria = None
    productos = contenedor.obtener().productos.listar(tipo=tipo, categoria=categoria)
    return render_template("admin/inventario.html", productos=productos, tipos=TIPOS,
                           tipo_actual=tipo, categorias=categorias, categoria_actual=categoria)


@bp.route("/productos/nuevo/<tipo>", methods=["GET", "POST"])
@sesion.solo_administradores
def nuevo_producto(tipo):
    if tipo not in TIPOS:
        abort(404)
    clase = TIPOS[tipo]
    if request.method == "POST":
        try:
            producto = contenedor.obtener().inventario.crear(tipo, request.form,
                                                             request.files.get("imagen"))
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            flash(f"«{producto.nombre}» se agregó al inventario.", "exito")
            return redirect(url_for("admin.inventario", tipo=tipo))
    return render_template("admin/producto_form.html", clase=clase, producto=None,
                           datos=request.form)


@bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@sesion.solo_administradores
def editar_producto(producto_id):
    c = contenedor.obtener()
    producto = c.productos.buscar_por_id(producto_id)
    if producto is None:
        abort(404)
    if request.method == "POST":
        try:
            c.inventario.actualizar(producto_id, request.form, request.files.get("imagen"))
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            flash("Cambios guardados.", "exito")
            return redirect(url_for("admin.inventario", tipo=producto.tipo))
    return render_template("admin/producto_form.html", clase=Producto.clase_para(producto.tipo),
                           producto=producto, datos=request.form)


@bp.route("/productos/<int:producto_id>/visibilidad", methods=["POST"])
@sesion.solo_administradores
def cambiar_visibilidad(producto_id):
    try:
        producto = contenedor.obtener().inventario.cambiar_visibilidad(producto_id)
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        estado = "visible para estudiantes" if producto.activo else "oculto para estudiantes"
        flash(f"«{producto.nombre}» ahora está {estado}.", "exito")
    return _regresar()


@bp.route("/productos/<int:producto_id>/reponer", methods=["POST"])
@sesion.solo_administradores
def reponer(producto_id):
    try:
        producto = contenedor.obtener().inventario.reponer(producto_id,
                                                           request.form.get("cantidad"))
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        flash(f"«{producto.nombre}» ahora tiene {producto.existencias} en existencia.", "exito")
    return _regresar()


@bp.route("/productos/<int:producto_id>/eliminar", methods=["GET", "POST"])
@sesion.solo_administradores
def eliminar_producto(producto_id):
    """GET muestra la confirmación; POST borra el producto."""
    c = contenedor.obtener()
    producto = c.productos.buscar_por_id(producto_id)
    if producto is None:
        abort(404)
    if request.method == "POST":
        try:
            c.inventario.eliminar(producto_id)
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            flash(f"«{producto.nombre}» se eliminó del inventario.", "exito")
        return redirect(url_for("admin.inventario", tipo=producto.tipo))
    return render_template("admin/confirmar_eliminar.html", producto=producto)


@bp.route("/pedidos")
@sesion.solo_administradores
def pedidos():
    """Lista de pedidos. Con ?codigo=KV-... busca el pedido que el estudiante muestra en la barra."""
    c = contenedor.obtener()
    nombres_pago = {m.CLAVE: m.nombre() for m in MetodoPago.disponibles()}
    codigo = request.args.get("codigo", "").strip()
    encontrado = None
    if codigo:
        try:
            encontrado = c.servicio_pedidos.buscar_por_codigo(codigo)
        except ErrorCafeteria as error:
            flash(str(error), "error")
    estado = request.args.get("estado")
    if estado not in [e.value for e in EstadoPedido]:
        estado = None
    lista = c.pedidos.listar(estado=estado)
    return render_template("admin/pedidos.html", pedidos=lista, estados=list(EstadoPedido),
                           estado_actual=estado, nombres_pago=nombres_pago,
                           codigo=codigo, encontrado=encontrado)


@bp.route("/pedidos/<int:pedido_id>/entregado", methods=["POST"])
@sesion.solo_administradores
def marcar_entregado(pedido_id):
    try:
        pedido = contenedor.obtener().servicio_pedidos.marcar_entregado(pedido_id)
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        flash(f"Pedido {pedido.codigo} de {pedido.nombre_cliente} entregado.", "exito")
    return _regresar_a_pedidos()


@bp.route("/pedidos/<int:pedido_id>/no-recogido", methods=["POST"])
@sesion.solo_administradores
def marcar_no_recogido(pedido_id):
    try:
        pedido = contenedor.obtener().servicio_pedidos.marcar_no_recogido(pedido_id)
    except ErrorCafeteria as error:
        flash(str(error), "error")
    else:
        flash(f"Pedido {pedido.codigo} marcado como no recogido.", "aviso")
    return _regresar_a_pedidos()


def _regresar_a_pedidos():
    anterior = request.referrer or ""
    if anterior.startswith(request.host_url):
        return redirect(anterior)
    return redirect(url_for("admin.pedidos"))


@bp.route("/reportes")
@sesion.solo_administradores
def reportes():
    """Reporte mensual de ventas (los cuadros de fin de mes de la gerencia)."""
    c = contenedor.obtener()
    try:
        reporte = c.reportes.reporte(request.args.get("mes"))
    except ErrorCafeteria as error:
        flash(str(error), "error")
        reporte = c.reportes.reporte()             # vuelve al mes actual
    return render_template("admin/reportes.html", reporte=reporte)


@bp.route("/reportes/descargar")
@sesion.solo_administradores
def descargar_reporte():
    try:
        reporte = contenedor.obtener().reportes.reporte(request.args.get("mes"))
    except ErrorCafeteria as error:
        flash(str(error), "error")
        return redirect(url_for("admin.reportes"))
    return Response(
        reporte.a_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte-ventas-{reporte.clave}.csv"},
    )
