"""Inicio, registro, inicio de sesión, cierre de sesión y recuperación de contraseña."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import contenedor
import sesion
from modelos.excepciones import ErrorCafeteria
from modelos.usuario import Usuario

bp = Blueprint("auth", __name__)


def _destino_seguro(siguiente, usuario):
    """Solo redirige a rutas internas (que empiezan con '/'), nunca a otro sitio."""
    if siguiente and siguiente.startswith("/") and not siguiente.startswith("//"):
        return siguiente
    return url_for(usuario.pagina_principal())


@bp.route("/")
def inicio():
    return render_template("inicio.html")


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if sesion.usuario_actual():
        return redirect(url_for(sesion.usuario_actual().pagina_principal()))
    if request.method == "POST":
        f = request.form
        try:
            estudiante = contenedor.obtener().autenticacion.registrar_estudiante(
                f.get("nombre"), f.get("correo"), f.get("contrasena", ""),
                f.get("confirmacion", ""), f.get("pregunta"), f.get("respuesta"),
            )
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            sesion.iniciar(estudiante)
            flash(f"¡Bienvenida/o, {estudiante.nombre}! Tu cuenta fue creada.", "exito")
            return redirect(url_for(estudiante.pagina_principal()))
    return render_template("auth/registro.html", preguntas=Usuario.PREGUNTAS_SEGURIDAD)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if sesion.usuario_actual():
        return redirect(url_for(sesion.usuario_actual().pagina_principal()))
    if request.method == "POST":
        try:
            usuario = contenedor.obtener().autenticacion.iniciar_sesion(
                request.form.get("correo"), request.form.get("contrasena"))
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            sesion.iniciar(usuario)
            flash(f"Hola, {usuario.nombre}.", "exito")
            return redirect(_destino_seguro(request.args.get("siguiente"), usuario))
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    sesion.cerrar()
    flash("Cerraste sesión.", "exito")
    return redirect(url_for("auth.inicio"))


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    """Paso 1: la persona escribe su correo."""
    if request.method == "POST":
        correo = request.form.get("correo", "")
        try:
            contenedor.obtener().autenticacion.obtener_pregunta(correo)
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            session["correo_recuperacion"] = Usuario.normalizar_correo(correo)
            return redirect(url_for("auth.recuperar_pregunta"))
    return render_template("auth/recuperar.html")


@bp.route("/recuperar/pregunta", methods=["GET", "POST"])
def recuperar_pregunta():
    """Paso 2: responde su pregunta de seguridad y elige una contraseña nueva."""
    correo = session.get("correo_recuperacion")
    if not correo:
        return redirect(url_for("auth.recuperar"))
    servicio = contenedor.obtener().autenticacion
    try:
        pregunta = servicio.obtener_pregunta(correo)
    except ErrorCafeteria:
        session.pop("correo_recuperacion", None)
        return redirect(url_for("auth.recuperar"))

    if request.method == "POST":
        f = request.form
        try:
            servicio.restablecer_contrasena(correo, f.get("respuesta"),
                                            f.get("contrasena", ""), f.get("confirmacion", ""))
        except ErrorCafeteria as error:
            flash(str(error), "error")
        else:
            session.pop("correo_recuperacion", None)
            flash("Tu contraseña se cambió. Ya puedes iniciar sesión.", "exito")
            return redirect(url_for("auth.login"))
    return render_template("auth/recuperar_pregunta.html", correo=correo, pregunta=pregunta)
