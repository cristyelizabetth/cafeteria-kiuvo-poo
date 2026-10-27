"""Productos: Producto (abstracta) → Almuerzo y ProductoTienda."""

import math
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
    TABLA_DETALLE = None   # tabla de la base de datos con los datos propios de cada tipo
    UMBRAL_EXISTENCIAS_BAJAS = 5

    # Rangos permitidos (validación de rangos)
    LONGITUD_NOMBRE = 80
    LONGITUD_DESCRIPCION = 300
    LONGITUD_DETALLE = 120
    PRECIO_MAXIMO = 100.00
    EXISTENCIAS_MAXIMAS = 9999
    REPOSICION_MAXIMA = 1000

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
    def tipos():
        """Todas las clases hijas de Producto que existen en el sistema."""
        return (Almuerzo, ProductoTienda)

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
        valor = " ".join((valor or "").split())    # quita espacios de más
        if not valor:
            raise DatosInvalidos("El nombre no puede estar vacío.")
        if len(valor) > self.LONGITUD_NOMBRE:
            raise DatosInvalidos(
                f"El nombre puede tener como máximo {self.LONGITUD_NOMBRE} caracteres.")
        self._nombre = valor

    @property
    def descripcion(self):
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor):
        valor = (valor or "").strip()
        if len(valor) > self.LONGITUD_DESCRIPCION:
            raise DatosInvalidos(
                f"La descripción puede tener como máximo {self.LONGITUD_DESCRIPCION} caracteres.")
        self._descripcion = valor

    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, valor):
        if not valor:
            raise DatosInvalidos("Elige una categoría.")
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
        if valor is None or str(valor).strip() == "":
            raise DatosInvalidos("Escribe el precio.")
        try:
            valor = round(float(valor), 2)
        except (TypeError, ValueError):
            raise DatosInvalidos("El precio debe ser un número, por ejemplo 3.50.") from None
        if not math.isfinite(valor):
            raise DatosInvalidos("El precio debe ser un número, por ejemplo 3.50.")
        if valor < 0:
            raise DatosInvalidos("El precio no puede ser negativo.")
        if valor > self.PRECIO_MAXIMO:
            raise DatosInvalidos(f"El precio no puede ser mayor que ${self.PRECIO_MAXIMO:.2f}.")
        self._precio = valor

    @property
    def existencias(self):
        return self._existencias

    @existencias.setter
    def existencias(self, valor):
        if valor is None or str(valor).strip() == "":
            raise DatosInvalidos("Escribe las existencias.")
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise DatosInvalidos("Las existencias deben ser un número entero, sin decimales.") from None
        if valor < 0:
            raise DatosInvalidos("Las existencias no pueden ser negativas.")
        if valor > self.EXISTENCIAS_MAXIMAS:
            raise DatosInvalidos(f"Las existencias no pueden pasar de {self.EXISTENCIAS_MAXIMAS}.")
        self._existencias = valor

    @property
    def activo(self):
        return self._activo

    @property
    def tipo(self):
        return self.TIPO

    @classmethod
    def _validar_detalle(cls, valor, nombre_campo):
        """Validación común de los datos propios de cada tipo (incluye / presentación)."""
        valor = " ".join((valor or "").split())
        if len(valor) > cls.LONGITUD_DETALLE:
            raise DatosInvalidos(
                f"{nombre_campo} puede tener como máximo {cls.LONGITUD_DETALLE} caracteres.")
        return valor

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
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            raise DatosInvalidos("La cantidad a reponer debe ser un número entero.") from None
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad a reponer debe ser mayor que cero.")
        if cantidad > self.REPOSICION_MAXIMA:
            raise DatosInvalidos(f"Puedes reponer como máximo {self.REPOSICION_MAXIMA} a la vez.")
        self.existencias = self._existencias + cantidad   # el setter revisa el máximo

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
        """Datos propios de este tipo, para su tabla de detalle en la base de datos.

        Devuelve {columna: valor}. Cada clase hija guarda sus datos propios en
        su propia tabla (TABLA_DETALLE): Almuerzo en 'almuerzos' y
        ProductoTienda en 'productos_tienda'.
        """

    def __repr__(self):
        return f"<{type(self).__name__} {self._nombre!r} x{self._existencias}>"


class Almuerzo(Producto):
    """Plato del menú que el estudiante reserva."""

    TIPO = "almuerzo"
    NOMBRE_TIPO = "Almuerzo"
    CATEGORIAS = ("Plato del día", "Vegetariano", "Ligero")
    TABLA_DETALLE = "almuerzos"
    UMBRAL_EXISTENCIAS_BAJAS = 5

    def __init__(self, nombre, descripcion, categoria, precio, existencias,
                 incluye="", activo=True, id=None, **_otros):
        super().__init__(nombre, descripcion, categoria, precio, existencias, activo, id)
        self.incluye = incluye

    @property
    def incluye(self):
        return self._incluye

    @incluye.setter
    def incluye(self, valor):
        self._incluye = self._validar_detalle(valor, "El campo «Incluye»")

    def texto_boton(self):
        return "Reservar"

    def etiqueta_existencias(self):
        n = self.existencias
        return f"Queda {n} porción" if n == 1 else f"Quedan {n} porciones"

    def detalle_extra(self):
        return f"Incluye: {self.incluye}" if self.incluye else ""

    def datos_extra(self):
        return {"incluye": self.incluye}


class ProductoTienda(Producto):
    """Producto empacado de la tienda (bebidas, snacks, postres)."""

    TIPO = "tienda"
    NOMBRE_TIPO = "Producto de tienda"
    CATEGORIAS = ("Bebidas", "Snacks", "Postres")
    TABLA_DETALLE = "productos_tienda"
    UMBRAL_EXISTENCIAS_BAJAS = 10

    def __init__(self, nombre, descripcion, categoria, precio, existencias,
                 presentacion="", activo=True, id=None, **_otros):
        super().__init__(nombre, descripcion, categoria, precio, existencias, activo, id)
        self.presentacion = presentacion

    @property
    def presentacion(self):
        return self._presentacion

    @presentacion.setter
    def presentacion(self, valor):
        self._presentacion = self._validar_detalle(valor, "La presentación")

    def texto_boton(self):
        return "Agregar al carrito"

    def etiqueta_existencias(self):
        return f"{self.existencias} disponible(s)"

    def detalle_extra(self):
        return self.presentacion

    def datos_extra(self):
        return {"presentacion": self.presentacion}
