"""Fotos de los productos: guardar, validar y borrar los archivos que sube el administrador."""

import secrets
import unicodedata
from pathlib import Path

from modelos.excepciones import ImagenInvalida
from modelos.producto import Producto


class GestorImagenes:
    """Se encarga de los archivos de imagen de los productos.

    - Solo acepta JPG, PNG y WEBP de hasta 2 MB.
    - Revisa el CONTENIDO del archivo (sus primeros bytes), no solo la
      extensión: un .exe renombrado a foto.jpg se rechaza.
    - Guarda cada foto con un nombre aleatorio (por ejemplo
      3f9a…c1.jpg), así nadie puede sobrescribir otro archivo ni
      colar una ruta peligrosa en el nombre.
    - Las fotos se guardan en instancia/imagenes, que no se sube a GitHub.
    """

    TAMANO_MAXIMO = 2 * 1024 * 1024   # 2 MB

    # Primeros bytes ("firma") de cada formato
    FIRMAS = {
        "jpg": [b"\xff\xd8\xff"],
        "png": [b"\x89PNG\r\n\x1a\n"],
    }

    # Ilustración que se muestra cuando un producto no tiene foto
    CARPETA_ILUSTRACIONES = "img/categorias"

    def __init__(self, carpeta):
        self._carpeta = Path(carpeta)
        self._carpeta.mkdir(parents=True, exist_ok=True)

    @property
    def carpeta(self):
        return self._carpeta

    # ---------- Guardar ----------
    def guardar(self, archivo):
        """Guarda la imagen subida y devuelve su nombre nuevo.

        `archivo` es lo que llega del formulario (request.files["imagen"]).
        Devuelve None si no se eligió ningún archivo.
        """
        if archivo is None or not getattr(archivo, "filename", ""):
            return None
        contenido = archivo.read(self.TAMANO_MAXIMO + 1)
        if not contenido:
            raise ImagenInvalida("El archivo de la imagen está vacío.")
        if len(contenido) > self.TAMANO_MAXIMO:
            raise ImagenInvalida("La imagen pesa más de 2 MB. Elige una más liviana.")
        extension = self._detectar_formato(contenido)
        if extension is None:
            raise ImagenInvalida("El archivo no es una imagen JPG, PNG o WEBP.")

        nombre = f"{secrets.token_hex(16)}.{extension}"
        (self._carpeta / nombre).write_bytes(contenido)
        return nombre

    def _detectar_formato(self, contenido):
        for extension, firmas in self.FIRMAS.items():
            if any(contenido.startswith(f) for f in firmas):
                return extension
        if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
            return "webp"
        return None

    # ---------- Leer y borrar ----------
    def ruta(self, nombre):
        """Ruta del archivo en disco, o None si el nombre no es válido o no existe."""
        if not nombre or not Producto.PATRON_IMAGEN.match(nombre):
            return None
        ruta = self._carpeta / nombre
        return ruta if ruta.is_file() else None

    def eliminar(self, nombre):
        ruta = self.ruta(nombre)
        if ruta is not None:
            ruta.unlink()

    # ---------- Ilustraciones por categoría ----------
    @classmethod
    def ilustracion_para(cls, categoria):
        """'Plato del día' → 'img/categorias/plato-del-dia.svg'"""
        sin_tildes = unicodedata.normalize("NFKD", categoria).encode("ascii", "ignore").decode()
        nombre = "-".join(sin_tildes.lower().split())
        return f"{cls.CARPETA_ILUSTRACIONES}/{nombre}.svg"
