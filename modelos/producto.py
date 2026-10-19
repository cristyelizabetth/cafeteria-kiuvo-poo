"""Productos: Producto (abstracta) → Almuerzo y ProductoTienda."""

from abc import ABC, abstractmethod

from modelos.excepciones import DatosInvalidos, InventarioInsuficiente


class Producto(ABC):
    """Todo lo que se vende en la cafetería.

    Las propiedades validan los datos: no se puede poner un precio negativo
    ni existencias negativas, aunque alguien lo intente desde un formulario.
    """

    TIPO = None
    NOMBRE_TIPO = None
    CATEGORIAS = ()
    UMBRAL_EXISTENCIAS_BAJAS = 5

    def __init__(self, nombre, descripcion, categoria, precio, existencias,
                 activo=True, id=None):
        self._id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.categoria = categoria
        self.precio = precio
        self.existencias = existencias
        self._activo = bool(activo)

    # ---------- Fábrica ----------
    @staticmethod
    def construir(tipo, **datos):
        """Devuelve un Almuerzo o un ProductoTienda según el tipo."""
        clases = {Almuerzo.TIPO: Almuerzo, ProductoTienda.TIPO: ProductoTienda}
        if tipo not in clases:
            raise DatosInvalidos(f"Tipo de producto desconocido: {tipo}")
        return clases[tipo](**datos)

    @staticmethod
    def clase_para(tipo):
        clases = {Almuerzo.TIPO: Almuerzo, ProductoTienda.TIPO: ProductoTienda}
        if tipo not in clases:
            raise DatosInvalidos(f"Tipo de producto desconocido: {tipo}")
        return clases[tipo]

    # ---------- Propiedades con validación ----------
    @property
    def id(self):
        return self._id

    def asignar_id(self, nuevo_id):
        if self._id is not None:
            raise ValueError("El producto ya tiene id.")
        self._id = nuevo_id

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        valor = (valor or "").strip()
        if not valor:
            raise DatosInvalidos("El nombre no puede estar vacío.")
        if len(valor) > 80:
            raise DatosInvalidos("El nombre puede tener como máximo 80 caracteres.")
        self._nombre = valor

    @property
    def descripcion(self):
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor):
        valor = (valor or "").strip()
        if len(valor) > 300:
            raise DatosInvalidos("La descripción puede tener como máximo 300 caracteres.")
        self._descripcion = valor

    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, valor):
        if valor not in self.CATEGORIAS:
            raise DatosInvalidos(
                f"Categoría no válida para {self.NOMBRE_TIPO.lower()}: {valor}"
            )
        self._categoria = valor

    @property
    def precio(self):
        return self._precio

    @precio.setter
    def precio(self, valor):
        try:
            valor = round(float(valor), 2)
        except (TypeError, ValueError):
            raise DatosInvalidos("El precio debe ser un número.") from None
        if valor < 0:
            raise DatosInvalidos("El precio no puede ser negativo.")
        self._precio = valor

    @property
    def existencias(self):
        return self._existencias

    @existencias.setter
    def existencias(self, valor):
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise DatosInvalidos("Las existencias deben ser un número entero.") from None
        if valor < 0:
            raise DatosInvalidos("Las existencias no pueden ser negativas.")
        self._existencias = valor

    @property
    def activo(self):
        return self._activo

    @property
    def tipo(self):
        return self.TIPO

    # ---------- Comportamiento ----------
    def esta_disponible(self):
        """Lo que ve el estudiante: activo y con existencias."""
        return self._activo and self._existencias > 0

    def hay_suficiente(self, cantidad):
        return cantidad <= self._existencias

    def descontar(self, cantidad):
        if not self.hay_suficiente(cantidad):
            raise InventarioInsuficiente(self._nombre, self._existencias)
        self._existencias -= cantidad

    def reponer(self, cantidad):
        cantidad = int(cantidad)
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad a reponer debe ser mayor que cero.")
        self._existencias += cantidad

    def activar(self):
        self._activo = True

    def desactivar(self):
        self._activo = False

    def existencias_bajas(self):
        return 0 < self._existencias <= self.UMBRAL_EXISTENCIAS_BAJAS

    def estado_inventario(self):
        """Texto para la tabla del administrador."""
        if not self._activo:
            return "Oculto"
        if self._existencias == 0:
            return "Agotado"
        if self.existencias_bajas():
            return "Bajo"
        return "Disponible"

    # ---------- Polimorfismo: cada tipo lo implementa distinto ----------
    @abstractmethod
    def texto_boton(self):
        """Texto del botón en el catálogo."""

    @abstractmethod
    def etiqueta_existencias(self):
        """Cómo se describen las existencias al estudiante."""

    @abstractmethod
    def detalle_extra(self):
        """Dato propio de cada tipo (qué incluye / presentación)."""

    @abstractmethod
    def datos_extra(self):
        """Columnas extra para guardar en la base de datos."""

    def __repr__(self):
        return f"<{type(self).__name__} {self._nombre!r} x{self._existencias}>"


class Almuerzo(Producto):
    """Plato del menú que el estudiante reserva."""

    TIPO = "almuerzo"
    NOMBRE_TIPO = "Almuerzo"
    CATEGORIAS = ("Plato del día", "Vegetariano", "Ligero")
    UMBRAL_EXISTENCIAS_BAJAS = 5

    def __init__(self, nombre, descripcion, categoria, precio, existencias,
                 incluye="", activo=True, id=None, **_otros):
        super().__init__(nombre, descripcion, categoria, precio, existencias, activo, id)
        self.incluye = (incluye or "").strip()

    def texto_boton(self):
        return "Reservar"

    def etiqueta_existencias(self):
        n = self.existencias
        return f"Queda {n} porción" if n == 1 else f"Quedan {n} porciones"

    def detalle_extra(self):
        return f"Incluye: {self.incluye}" if self.incluye else ""

    def datos_extra(self):
        return {"incluye": self.incluye, "presentacion": None}


class ProductoTienda(Producto):
    """Producto empacado de la tienda (bebidas, snacks, postres)."""

    TIPO = "tienda"
    NOMBRE_TIPO = "Producto de tienda"
    CATEGORIAS = ("Bebidas", "Snacks", "Postres")
    UMBRAL_EXISTENCIAS_BAJAS = 10

    def __init__(self, nombre, descripcion, categoria, precio, existencias,
                 presentacion="", activo=True, id=None, **_otros):
        super().__init__(nombre, descripcion, categoria, precio, existencias, activo, id)
        self.presentacion = (presentacion or "").strip()

    def texto_boton(self):
        return "Agregar al carrito"

    def etiqueta_existencias(self):
        return f"{self.existencias} disponible(s)"

    def detalle_extra(self):
        return self.presentacion

    def datos_extra(self):
        return {"incluye": None, "presentacion": self.presentacion}
