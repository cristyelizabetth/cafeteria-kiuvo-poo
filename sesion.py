"""Manejo de la sesión: quién inició sesión, permisos por rol y carrito."""

from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

import contenedor
from modelos.carrito import Carrito


def usuario_actual():
    """Devuelve el objeto Usuario de la sesión (o None). Se carga una vez por petición."""
    if "usuario" not in g:
        usuario_id = session.get("usuario_id")
        g.usuario = contenedor.obtener().usuarios.buscar_por_id(usuario_id) if usuario_id else None
    return g.usuario


def iniciar(usuario):
    # session.clear() borra cualquier dato anterior (evita "fijación de sesión")
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario.id
    g.usuario = usuario


def cerrar():
    session.clear()
    g.usuario = None


# ---------- Decoradores de control de acceso ----------
def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            flash("Inicia sesión para continuar.", "aviso")
            return redirect(url_for("auth.login", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


def solo_compradores(vista):
    """Solo usuarios que pueden comprar (estudiantes). El admin recibe 403."""
    @wraps(vista)
    @login_requerido
    def envoltura(*args, **kwargs):
        if not usuario_actual().puede_comprar():
            abort(403)
        return vista(*args, **kwargs)
    return envoltura


def solo_administradores(vista):
    @wraps(vista)
    @login_requerido
    def envoltura(*args, **kwargs):
        if not usuario_actual().puede_gestionar_inventario():
            abort(403)
        return vista(*args, **kwargs)
    return envoltura


# ---------- Carrito en la sesión ----------
def obtener_carrito():
    carrito = Carrito.desde_dict(session.get("carrito"), contenedor.obtener().productos)
    if carrito.avisos:
        for aviso in carrito.avisos:
            flash(aviso, "aviso")
        guardar_carrito(carrito)
    return carrito


def guardar_carrito(carrito):
    session["carrito"] = carrito.a_dict()
