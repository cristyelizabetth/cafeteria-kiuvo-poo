"""Punto de entrada: crea la aplicación Flask y une todas las piezas.

Ejecutar con:   python app.py
"""

from datetime import datetime

from flask import Flask, abort, render_template, request, session

import contenedor
import sesion
from base_datos import BaseDatos
from config import Configuracion
from datos_iniciales import cargar_datos_iniciales
from modelos.excepciones import ErrorBaseDatos
from dao import CategoriaDAO, PedidoDAO, ProductoDAO, UsuarioDAO
from rutas import admin, auth, estudiante
from seguridad import LimitadorIntentos, ProtectorCSRF
from servicios import ServicioAutenticacion, ServicioInventario, ServicioPedidos


def crear_app(configuracion=Configuracion):
    app = Flask(__name__)
    app.config.from_object(configuracion)

    # 1. Base de datos y capa DAO
    base_datos = BaseDatos(app.config["BASE_DATOS"])
    base_datos.inicializar()
    usuarios = UsuarioDAO(base_datos)
    categorias = CategoriaDAO(base_datos)
    productos = ProductoDAO(base_datos)
    pedidos = PedidoDAO(base_datos)
    cargar_datos_iniciales(usuarios, categorias, productos)

    # 2. Servicios (reglas del negocio)
    limitador_login = LimitadorIntentos(app.config["INTENTOS_LOGIN"], app.config["SEGUNDOS_BLOQUEO"])
    limitador_recuperacion = LimitadorIntentos(app.config["INTENTOS_LOGIN"],
                                               app.config["SEGUNDOS_BLOQUEO"])
    csrf = ProtectorCSRF()
    app.extensions[contenedor.CLAVE_EXTENSION] = contenedor.Contenedor(
        base_datos=base_datos,
        usuarios=usuarios,
        categorias=categorias,
        productos=productos,
        pedidos=pedidos,
        autenticacion=ServicioAutenticacion(usuarios, limitador_login, limitador_recuperacion),
        servicio_pedidos=ServicioPedidos(productos, pedidos),
        inventario=ServicioInventario(productos),
        csrf=csrf,
    )

    # 3. Rutas
    app.register_blueprint(auth.bp)
    app.register_blueprint(estudiante.bp)
    app.register_blueprint(admin.bp)

    # 4. Seguridad en cada petición
    @app.before_request
    def revisar_csrf():
        if request.method == "POST":
            if not csrf.es_valido(session, request.form.get(ProtectorCSRF.NOMBRE_CAMPO)):
                abort(400, description="El formulario expiró. Recarga la página e inténtalo de nuevo.")

    @app.after_request
    def encabezados_seguridad(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "same-origin"
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        return respuesta

    # 5. Variables y filtros disponibles en todas las plantillas
    @app.context_processor
    def variables_globales():
        try:
            usuario = sesion.usuario_actual()
        except ErrorBaseDatos:
            usuario = None          # para poder mostrar la página de error igual
        cantidad_carrito = 0
        if usuario and usuario.puede_comprar():
            cantidad_carrito = sum(session.get("carrito", {}).values())
        return {
            "usuario": usuario,
            "cantidad_carrito": cantidad_carrito,
            "csrf_token": lambda: csrf.token(session),
        }

    @app.template_filter("dinero")
    def dinero(valor):
        return f"${valor:,.2f}"

    @app.template_filter("fecha")
    def fecha(valor):
        try:
            return datetime.strptime(valor, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            return valor

    # 6. Páginas de error
    def pagina_error(codigo, titulo, mensaje):
        return render_template("error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo

    @app.errorhandler(400)
    def error_400(error):
        return pagina_error(400, "Solicitud no válida", error.description)

    @app.errorhandler(403)
    def error_403(error):
        return pagina_error(403, "Acceso denegado", "Tu cuenta no tiene permiso para ver esta página.")

    @app.errorhandler(404)
    def error_404(error):
        return pagina_error(404, "Página no encontrada", "La página que buscas no existe.")

    @app.errorhandler(ErrorBaseDatos)
    def error_base_datos(error):
        # Si la base de datos falla en cualquier página, se muestra un mensaje claro
        return pagina_error(503, "Base de datos no disponible", str(error))

    @app.errorhandler(500)
    def error_500(error):
        return pagina_error(500, "Error del servidor", "Algo salió mal. Inténtalo más tarde.")

    return app


if __name__ == "__main__":
    aplicacion = crear_app()
    aplicacion.run(debug=aplicacion.config["DEBUG"])
