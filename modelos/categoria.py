"""Categoría de un producto (tabla categorias)."""

from modelos.excepciones import DatosInvalidos


class Categoria:
    """Una categoría del menú o de la tienda: "Bebidas", "Vegetariano"…

    Cada categoría pertenece a un tipo de producto ('almuerzo' o 'tienda'),
    así un almuerzo nunca puede quedar en "Bebidas".
    """

    TIPOS_VALIDOS = ("almuerzo", "tienda")
    LONGITUD_MAXIMA = 40

    def __init__(self, nombre, tipo, id=None):
        self._id = id
        self.nombre = nombre
        self.tipo = tipo

    @property
    def id(self):
        return self._id

    def asignar_id(self, nuevo_id):
        if self._id is not None:
            raise ValueError("La categoría ya tiene id.")
        self._id = nuevo_id

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        valor = " ".join((valor or "").split())
        if not valor:
            raise DatosInvalidos("El nombre de la categoría no puede estar vacío.")
        if len(valor) > self.LONGITUD_MAXIMA:
            raise DatosInvalidos(
                f"El nombre de la categoría puede tener como máximo {self.LONGITUD_MAXIMA} caracteres.")
        self._nombre = valor

    @property
    def tipo(self):
        return self._tipo

    @tipo.setter
    def tipo(self, valor):
        if valor not in self.TIPOS_VALIDOS:
            raise DatosInvalidos(f"Tipo de categoría no válido: {valor}")
        self._tipo = valor

    def __repr__(self):
        return f"<Categoria {self._nombre!r} ({self._tipo})>"
