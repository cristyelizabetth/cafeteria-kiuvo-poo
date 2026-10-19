"""Usuarios del sistema: Usuario (abstracta) → Estudiante y Administrador."""

from abc import ABC, abstractmethod

from werkzeug.security import check_password_hash, generate_password_hash

from seguridad import ValidadorContrasena


class Usuario(ABC):
    """Clase abstracta: no se puede crear un 'Usuario' genérico, solo sus hijas.

    Encapsulamiento: el hash de la contraseña y el de la respuesta de seguridad
    son atributos privados (__). Nadie de afuera puede leer la contraseña ni
    cambiarla directamente; hay que usar los métodos de la clase.
    """

    ROL = None  # cada clase hija define el suyo

    PREGUNTAS_SEGURIDAD = (
        "¿Cuál es el nombre de tu primera mascota?",
        "¿Cómo se llamaba tu escuela primaria?",
        "¿Cuál es tu comida favorita?",
        "¿En qué ciudad nació tu mamá o tu papá?",
        "¿Cuál es el segundo nombre de tu mejor amigo o amiga?",
    )

    def __init__(self, nombre, correo, password_hash, pregunta_seguridad,
                 respuesta_hash, id=None):
        self._id = id
        self._nombre = nombre.strip()
        self._correo = Usuario.normalizar_correo(correo)
        self.__password_hash = password_hash
        self._pregunta_seguridad = pregunta_seguridad
        self.__respuesta_hash = respuesta_hash

    # ---------- Creación ----------
    @classmethod
    def crear(cls, nombre, correo, contrasena, pregunta, respuesta):
        """Crea un usuario nuevo a partir de datos en texto plano.

        La contraseña y la respuesta se convierten en hash aquí mismo;
        el texto original nunca se guarda.
        """
        ValidadorContrasena.validar(contrasena)
        return cls(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(contrasena),
            pregunta_seguridad=pregunta,
            respuesta_hash=generate_password_hash(cls.normalizar_respuesta(respuesta)),
        )

    @staticmethod
    def construir(rol, **datos):
        """Fábrica: devuelve un Estudiante o un Administrador según el rol."""
        clases = {Estudiante.ROL: Estudiante, Administrador.ROL: Administrador}
        if rol not in clases:
            raise ValueError(f"Rol desconocido: {rol}")
        return clases[rol](**datos)

    @staticmethod
    def normalizar_correo(correo):
        return correo.strip().lower()

    @staticmethod
    def normalizar_respuesta(respuesta):
        """'  Pupusas ' y 'pupusas' cuentan como la misma respuesta."""
        return " ".join(respuesta.lower().split())

    # ---------- Contraseña y respuesta de seguridad ----------
    def verificar_contrasena(self, contrasena):
        return check_password_hash(self.__password_hash, contrasena)

    def cambiar_contrasena(self, nueva):
        ValidadorContrasena.validar(nueva)
        self.__password_hash = generate_password_hash(nueva)

    def verificar_respuesta(self, respuesta):
        return check_password_hash(self.__respuesta_hash,
                                   self.normalizar_respuesta(respuesta))

    # ---------- Propiedades (solo lectura) ----------
    @property
    def id(self):
        return self._id

    def asignar_id(self, nuevo_id):
        """Lo usa el repositorio después de guardar el usuario por primera vez."""
        if self._id is not None:
            raise ValueError("El usuario ya tiene id.")
        self._id = nuevo_id

    @property
    def nombre(self):
        return self._nombre

    @property
    def correo(self):
        return self._correo

    @property
    def rol(self):
        return self.ROL

    @property
    def pregunta_seguridad(self):
        return self._pregunta_seguridad

    @property
    def password_hash(self):
        """Solo para que el repositorio lo guarde. Es un hash, no la contraseña."""
        return self.__password_hash

    @property
    def respuesta_hash(self):
        return self.__respuesta_hash

    # ---------- Métodos que cada hija implementa a su manera (polimorfismo) ----------
    @abstractmethod
    def puede_comprar(self):
        """¿Puede usar el carrito, reservar y pagar?"""

    @abstractmethod
    def pagina_principal(self):
        """Nombre de la ruta a la que se envía al usuario al iniciar sesión."""

    @abstractmethod
    def descripcion_rol(self):
        """Texto que se muestra en la barra de navegación."""

    def puede_gestionar_inventario(self):
        return False

    def __repr__(self):
        return f"<{type(self).__name__} {self._correo}>"


class Estudiante(Usuario):
    """Cliente de la cafetería: reserva almuerzos y compra en la tienda."""

    ROL = "estudiante"

    def puede_comprar(self):
        return True

    def pagina_principal(self):
        return "estudiante.almuerzos"

    def descripcion_rol(self):
        return "Estudiante"


class Administrador(Usuario):
    """Personal de la cafetería: solo gestiona almuerzos e inventario.

    No puede comprar ni reservar (puede_comprar devuelve False).
    """

    ROL = "administrador"

    def puede_comprar(self):
        return False

    def pagina_principal(self):
        return "admin.panel"

    def descripcion_rol(self):
        return "Administrador"

    def puede_gestionar_inventario(self):
        return True
