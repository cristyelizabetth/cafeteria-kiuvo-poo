"""Interfaz DAO: la clase abstracta que todos los DAO implementan.

DAO = Data Access Object (objeto de acceso a datos). Es la ÚNICA capa del
programa que habla con la base de datos. Las rutas (interfaz) y los servicios
(lógica) nunca escriben SQL: le piden los datos a un DAO.

    Rutas (interfaz)  →  Servicios (lógica)  →  DAO (datos)  →  SQLite
"""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager

from modelos.excepciones import (ErrorBaseDatos, ErrorCafeteria, RegistroDuplicado,
                                 RegistroEnUso, RegistroNoEncontrado)


class DAO(ABC):
    """Contrato que cumple cada DAO: las cuatro operaciones CRUD.

        C  insertar(entidad)       → INSERT
        R  buscar_por_id(id)       → SELECT ... WHERE id = ?
           listar(**filtros)       → SELECT con filtros opcionales
        U  actualizar(entidad)     → UPDATE
        D  eliminar(id)            → DELETE

    Además, todos los DAO:
      - usan consultas parametrizadas (?) para evitar la inyección SQL;
      - hacen cada operación dentro de una transacción (todo o nada);
      - convierten los errores de SQLite en excepciones propias con
        mensajes que el usuario entiende (método _conexion).
    """

    # Mensajes que cada DAO puede personalizar
    MENSAJE_DUPLICADO = "Ya existe un registro con esos datos."
    MENSAJE_EN_USO = "No se puede eliminar porque otros datos dependen de este registro."
    MENSAJE_NO_ENCONTRADO = "El registro que buscas no existe."

    def __init__(self, base_datos):
        self._bd = base_datos

    # ---------- Operaciones CRUD (cada DAO las implementa) ----------
    @abstractmethod
    def insertar(self, entidad):
        """Guarda una entidad nueva y le asigna su id."""

    @abstractmethod
    def buscar_por_id(self, id):
        """Devuelve la entidad con ese id, o None si no existe."""

    @abstractmethod
    def listar(self, **filtros):
        """Devuelve una lista de entidades (con filtros opcionales)."""

    @abstractmethod
    def actualizar(self, entidad):
        """Guarda los cambios de una entidad que ya existe."""

    @abstractmethod
    def eliminar(self, id):
        """Borra la entidad con ese id."""

    @abstractmethod
    def _a_objeto(self, fila):
        """Convierte una fila de la base de datos en un objeto del modelo."""

    # ---------- Comunes a todos los DAO ----------
    def guardar(self, entidad):
        """Inserta si es nueva (sin id) o actualiza si ya existe."""
        if entidad.id is None:
            return self.insertar(entidad)
        return self.actualizar(entidad)

    @contextmanager
    def _conexion(self):
        """Abre una transacción y traduce los errores de SQLite.

        Uso dentro de un DAO:
            with self._conexion() as con:
                con.execute("UPDATE ... WHERE id = ?", (id,))

        - Si todo sale bien se guarda (commit).
        - Si algo falla se deshace todo (rollback) y se lanza una
          excepción propia en vez del error técnico de SQLite.
        """
        try:
            with self._bd.conexion() as con:
                yield con
        except ErrorCafeteria:
            raise                          # errores del negocio: pasan tal cual
        except sqlite3.IntegrityError as error:
            mensaje = str(error)
            if "UNIQUE" in mensaje:
                raise RegistroDuplicado(self.MENSAJE_DUPLICADO) from error
            if "FOREIGN KEY" in mensaje:
                raise RegistroEnUso(self.MENSAJE_EN_USO) from error
            raise ErrorBaseDatos("Los datos no cumplen las reglas de la base de datos.") from error
        except sqlite3.Error as error:
            raise ErrorBaseDatos(
                "No se pudo acceder a la base de datos. Intenta de nuevo en un momento.") from error

    def _confirmar_afectadas(self, cursor):
        """Lanza RegistroNoEncontrado si un UPDATE o DELETE no tocó ninguna fila."""
        if cursor.rowcount == 0:
            raise RegistroNoEncontrado(self.MENSAJE_NO_ENCONTRADO)
