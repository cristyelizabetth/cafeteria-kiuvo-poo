"""Servicios: las reglas del negocio que usan varias clases a la vez.

Las rutas (páginas) llaman a estos servicios; los servicios usan los modelos
y la capa DAO. Así las rutas quedan cortas, la lógica no se repite y ningún
servicio escribe SQL.
"""

import re

from modelos.excepciones import (ContrasenaInvalida, CorreoYaRegistrado,
                                 CredencialesInvalidas, CuentaBloqueada,
                                 DatosInvalidos, ErrorCafeteria, PedidoNoCancelable,
                                 RegistroDuplicado)
from modelos.pago import MetodoPago
from modelos.pedido import Pedido
from modelos.producto import Producto
from modelos.usuario import Estudiante, Usuario

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$")   # letras, espacios, apóstrofo, punto y guion


class ServicioAutenticacion:
    """Registro, inicio de sesión y recuperación de contraseña."""

    def __init__(self, usuario_dao, limitador_login, limitador_recuperacion):
        self._usuarios = usuario_dao
        self._limitador_login = limitador_login
        self._limitador_recuperacion = limitador_recuperacion

    def registrar_estudiante(self, nombre, correo, contrasena, confirmacion,
                             pregunta, respuesta):
        """Solo se pueden registrar estudiantes; el administrador ya viene creado."""
        nombre = " ".join((nombre or "").split())
        correo = Usuario.normalizar_correo(correo or "")
        if not nombre:
            raise DatosInvalidos("Escribe tu nombre completo.")
        if len(nombre) < 3:
            raise DatosInvalidos("El nombre debe tener al menos 3 letras.")
        if len(nombre) > 80:
            raise DatosInvalidos("El nombre puede tener como máximo 80 caracteres.")
        if not PATRON_NOMBRE.match(nombre):
            raise DatosInvalidos("El nombre solo puede tener letras y espacios.")
        if not correo:
            raise DatosInvalidos("Escribe tu correo.")
        if not PATRON_CORREO.match(correo) or len(correo) > 120:
            raise DatosInvalidos("Escribe un correo válido, por ejemplo nombre@correo.com.")
        if not contrasena:
            raise ContrasenaInvalida("Escribe una contraseña.")
        if contrasena != confirmacion:
            raise ContrasenaInvalida("Las contraseñas no coinciden.")
        if pregunta not in Usuario.PREGUNTAS_SEGURIDAD:
            raise DatosInvalidos("Elige una pregunta de seguridad de la lista.")
        respuesta_limpia = Usuario.normalizar_respuesta(respuesta or "")
        if len(respuesta_limpia) < 2:
            raise DatosInvalidos("Escribe una respuesta a la pregunta de seguridad.")
        if len(respuesta_limpia) > 80:
            raise DatosInvalidos("La respuesta puede tener como máximo 80 caracteres.")
        if self._usuarios.existe_correo(correo):
            raise CorreoYaRegistrado("Ya existe una cuenta con ese correo.")

        estudiante = Estudiante.crear(nombre, correo, contrasena, pregunta, respuesta)
        try:
            return self._usuarios.insertar(estudiante)
        except RegistroDuplicado:
            # Por si dos personas se registran con el mismo correo al mismo tiempo
            raise CorreoYaRegistrado("Ya existe una cuenta con ese correo.") from None

    def iniciar_sesion(self, correo, contrasena):
        clave = Usuario.normalizar_correo(correo or "")
        # Campos vacíos: se avisa sin contarlo como intento fallido
        if not clave or not contrasena:
            raise DatosInvalidos("Escribe tu correo y tu contraseña.")
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
        if not (correo or "").strip():
            raise DatosInvalidos("Escribe tu correo.")
        usuario = self._usuarios.buscar_por_correo(correo)
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
        if not (respuesta or "").strip():
            raise DatosInvalidos("Escribe la respuesta a tu pregunta de seguridad.")
        if not nueva:
            raise ContrasenaInvalida("Escribe la contraseña nueva.")
        if not usuario.verificar_respuesta(respuesta):
            self._limitador_recuperacion.registrar_fallo(clave)
            restantes = self._limitador_recuperacion.segundos_restantes(clave)
            if restantes:
                raise CuentaBloqueada(restantes)
            raise CredencialesInvalidas("La respuesta de seguridad no es correcta.")
        if nueva != confirmacion:
            raise ContrasenaInvalida("Las contraseñas no coinciden.")

        usuario.cambiar_contrasena(nueva)
        self._usuarios.actualizar(usuario)
        self._limitador_recuperacion.reiniciar(clave)
        self._limitador_login.reiniciar(clave)
        return usuario


class ServicioPedidos:
    """Confirmar compras y cancelar pedidos."""

    def __init__(self, producto_dao, pedido_dao):
        self._productos = producto_dao
        self._pedidos = pedido_dao

    def confirmar_compra(self, usuario, carrito, clave_metodo):
        if not usuario.puede_comprar():
            raise ErrorCafeteria("Esta cuenta no puede realizar compras.")
        if carrito.esta_vacio():
            raise DatosInvalidos("Tu carrito está vacío.")
        metodo = MetodoPago.obtener(clave_metodo)
        if metodo is None:
            raise DatosInvalidos("Elige un método de pago.")

        pedido = Pedido.desde_carrito(usuario, carrito, metodo)
        self._pedidos.insertar(pedido)           # guarda y descuenta inventario
        mensaje = metodo.procesar(pedido.total)  # polimorfismo: cada método responde distinto
        return pedido, mensaje

    def cancelar(self, usuario, pedido_id):
        pedido = self._pedidos.buscar_por_id(pedido_id)
        if pedido is None or not pedido.pertenece_a(usuario):
            raise PedidoNoCancelable("No encontramos ese pedido.")
        pedido.cancelar()                      # el modelo revisa si se puede
        self._pedidos.cancelar(pedido)         # guarda y devuelve el inventario
        return pedido

    def pedidos_de(self, usuario):
        return self._pedidos.listar(usuario_id=usuario.id)


class ServicioInventario:
    """Lo que hace el administrador con los productos (CRUD completo)."""

    def __init__(self, producto_dao):
        self._productos = producto_dao

    # C
    def crear(self, tipo, formulario):
        datos = self._leer_formulario(formulario)
        producto = Producto.construir(tipo, **datos)     # las propiedades validan
        self._revisar_duplicado(producto)
        return self._guardar(self._productos.insertar, producto)

    # R
    def obtener(self, producto_id):
        producto = self._productos.buscar_por_id(producto_id)
        if producto is None:
            raise DatosInvalidos("Ese producto no existe.")
        return producto

    # U
    def actualizar(self, producto_id, formulario):
        producto = self.obtener(producto_id)
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
        self._revisar_duplicado(producto)
        return self._guardar(self._productos.actualizar, producto)

    def cambiar_visibilidad(self, producto_id):
        producto = self.obtener(producto_id)
        if producto.activo:
            producto.desactivar()
        else:
            producto.activar()
        return self._productos.actualizar(producto)

    def reponer(self, producto_id, cantidad):
        producto = self.obtener(producto_id)
        producto.reponer(cantidad)                      # el modelo valida la cantidad
        return self._productos.actualizar(producto)

    # D
    def eliminar(self, producto_id):
        """Borra el producto. Si ya se vendió, el DAO lanza RegistroEnUso
        con un mensaje que sugiere ocultarlo."""
        producto = self.obtener(producto_id)
        self._productos.eliminar(producto.id)
        return producto

    # ---------- Ayudantes ----------
    def _revisar_duplicado(self, producto):
        if self._productos.existe_nombre(producto.nombre, producto.tipo, excluir_id=producto.id):
            raise RegistroDuplicado(
                f"Ya existe un {producto.NOMBRE_TIPO.lower()} llamado «{producto.nombre}».")

    @staticmethod
    def _guardar(operacion, producto):
        """Ejecuta insertar/actualizar del DAO con un mensaje claro si el nombre se repite."""
        try:
            return operacion(producto)
        except RegistroDuplicado:
            raise RegistroDuplicado(
                f"Ya existe un {producto.NOMBRE_TIPO.lower()} llamado «{producto.nombre}».") from None

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
