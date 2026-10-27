"""Servicios: las reglas del negocio que usan varias clases a la vez.

Las rutas (páginas) llaman a estos servicios; los servicios usan los modelos
y los repositorios. Así las rutas quedan cortas y la lógica no se repite.
"""

import re

from modelos.excepciones import (ContrasenaInvalida, CorreoYaRegistrado,
                                 CredencialesInvalidas, CuentaBloqueada,
                                 DatosInvalidos, ErrorCafeteria, PedidoNoCancelable)
from modelos.pago import MetodoPago
from modelos.pedido import Pedido
from modelos.producto import Producto
from modelos.usuario import Estudiante, Usuario

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ServicioAutenticacion:
    """Registro, inicio de sesión y recuperación de contraseña."""

    def __init__(self, repo_usuarios, limitador_login, limitador_recuperacion):
        self._usuarios = repo_usuarios
        self._limitador_login = limitador_login
        self._limitador_recuperacion = limitador_recuperacion

    def registrar_estudiante(self, nombre, correo, contrasena, confirmacion,
                             pregunta, respuesta):
        """Solo se pueden registrar estudiantes; el administrador ya viene creado."""
        nombre = (nombre or "").strip()
        correo = Usuario.normalizar_correo(correo or "")
        if len(nombre) < 3:
            raise DatosInvalidos("Escribe tu nombre completo.")
        if len(nombre) > 80:
            raise DatosInvalidos("El nombre es demasiado largo.")
        if not PATRON_CORREO.match(correo) or len(correo) > 120:
            raise DatosInvalidos("Escribe un correo válido.")
        if contrasena != confirmacion:
            raise ContrasenaInvalida("Las contraseñas no coinciden.")
        if pregunta not in Usuario.PREGUNTAS_SEGURIDAD:
            raise DatosInvalidos("Elige una pregunta de seguridad de la lista.")
        if len(Usuario.normalizar_respuesta(respuesta or "")) < 2:
            raise DatosInvalidos("Escribe una respuesta a la pregunta de seguridad.")
        if self._usuarios.existe_correo(correo):
            raise CorreoYaRegistrado("Ya existe una cuenta con ese correo.")

        estudiante = Estudiante.crear(nombre, correo, contrasena, pregunta, respuesta)
        return self._usuarios.guardar(estudiante)

    def iniciar_sesion(self, correo, contrasena):
        clave = Usuario.normalizar_correo(correo or "")
        restantes = self._limitador_login.segundos_restantes(clave)
        if restantes:
            raise CuentaBloqueada(restantes)

        usuario = self._usuarios.buscar_por_correo(clave)
        if usuario is None or not usuario.verificar_contrasena(contrasena or ""):
            self._limitador_login.registrar_fallo(clave)
            restantes = self._limitador_login.segundos_restantes(clave)
            if restantes:
                raise CuentaBloqueada(restantes)
            # Mismo mensaje si el correo no existe o si la contraseña está mal:
            # así nadie puede averiguar qué correos están registrados.
            raise CredencialesInvalidas(
                "Correo o contraseña incorrectos. "
                f"Te quedan {self._limitador_login.intentos_restantes(clave)} intento(s)."
            )

        self._limitador_login.reiniciar(clave)
        return usuario

    def obtener_pregunta(self, correo):
        usuario = self._usuarios.buscar_por_correo(correo or "")
        if usuario is None:
            raise CredencialesInvalidas("No encontramos una cuenta con ese correo.")
        return usuario.pregunta_seguridad

    def restablecer_contrasena(self, correo, respuesta, nueva, confirmacion):
        clave = Usuario.normalizar_correo(correo or "")
        restantes = self._limitador_recuperacion.segundos_restantes(clave)
        if restantes:
            raise CuentaBloqueada(restantes)

        usuario = self._usuarios.buscar_por_correo(clave)
        if usuario is None:
            raise CredencialesInvalidas("No encontramos una cuenta con ese correo.")
        if not usuario.verificar_respuesta(respuesta or ""):
            self._limitador_recuperacion.registrar_fallo(clave)
            restantes = self._limitador_recuperacion.segundos_restantes(clave)
            if restantes:
                raise CuentaBloqueada(restantes)
            raise CredencialesInvalidas("La respuesta de seguridad no es correcta.")
        if nueva != confirmacion:
            raise ContrasenaInvalida("Las contraseñas no coinciden.")

        usuario.cambiar_contrasena(nueva)
        self._usuarios.guardar(usuario)
        self._limitador_recuperacion.reiniciar(clave)
        self._limitador_login.reiniciar(clave)
        return usuario


class ServicioPedidos:
    """Confirmar compras y cancelar pedidos."""

    def __init__(self, repo_productos, repo_pedidos):
        self._productos = repo_productos
        self._pedidos = repo_pedidos

    def confirmar_compra(self, usuario, carrito, clave_metodo):
        if not usuario.puede_comprar():
            raise ErrorCafeteria("Esta cuenta no puede realizar compras.")
        if carrito.esta_vacio():
            raise DatosInvalidos("Tu carrito está vacío.")
        metodo = MetodoPago.obtener(clave_metodo)
        if metodo is None:
            raise DatosInvalidos("Elige un método de pago.")

        pedido = Pedido.desde_carrito(usuario, carrito, metodo)
        self._pedidos.registrar(pedido)        # guarda y descuenta inventario
        mensaje = metodo.procesar(pedido.total)  # polimorfismo: cada método responde distinto
        return pedido, mensaje

    def cancelar(self, usuario, pedido_id):
        pedido = self._pedidos.buscar_por_id(pedido_id)
        if pedido is None or not pedido.pertenece_a(usuario):
            raise PedidoNoCancelable("No encontramos ese pedido.")
        pedido.cancelar()                      # el modelo revisa si se puede
        self._pedidos.guardar_cancelacion(pedido)
        return pedido

    def pedidos_de(self, usuario):
        return self._pedidos.listar_por_usuario(usuario.id)


class ServicioInventario:
    """Lo que hace el administrador con los productos."""

    def __init__(self, repo_productos):
        self._productos = repo_productos

    def crear(self, tipo, formulario):
        datos = self._leer_formulario(formulario)
        producto = Producto.construir(tipo, **datos)
        return self._productos.guardar(producto)

    def actualizar(self, producto_id, formulario):
        producto = self._obtener(producto_id)
        datos = self._leer_formulario(formulario)
        producto.nombre = datos["nombre"]
        producto.descripcion = datos["descripcion"]
        producto.categoria = datos["categoria"]
        producto.precio = datos["precio"]
        producto.existencias = datos["existencias"]
        if producto.tipo == "almuerzo":
            producto.incluye = datos["incluye"]
        else:
            producto.presentacion = datos["presentacion"]
        return self._productos.guardar(producto)

    def cambiar_visibilidad(self, producto_id):
        producto = self._obtener(producto_id)
        if producto.activo:
            producto.desactivar()
        else:
            producto.activar()
        return self._productos.guardar(producto)

    def reponer(self, producto_id, cantidad):
        producto = self._obtener(producto_id)
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            raise DatosInvalidos("Escribe una cantidad válida.") from None
        producto.reponer(cantidad)
        return self._productos.guardar(producto)

    def _obtener(self, producto_id):
        producto = self._productos.buscar_por_id(producto_id)
        if producto is None:
            raise DatosInvalidos("Ese producto no existe.")
        return producto

    @staticmethod
    def _leer_formulario(formulario):
        return {
            "nombre": formulario.get("nombre", ""),
            "descripcion": formulario.get("descripcion", ""),
            "categoria": formulario.get("categoria", ""),
            "precio": formulario.get("precio", ""),
            "existencias": formulario.get("existencias", ""),
            "incluye": formulario.get("incluye", ""),
            "presentacion": formulario.get("presentacion", ""),
        }
