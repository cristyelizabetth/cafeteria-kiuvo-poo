"""Reporte mensual de ventas: lo que la cafetería vendió en un mes.

La gerente arma sus cuadros el último día de cada mes. Este reporte le da
esa información lista: cuánto se vendió de cada producto y cuánto dinero
entró, además de cuántos pedidos se entregaron y cuántos no se recogieron.
"""

import csv
import io

from modelos.excepciones import DatosInvalidos

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")


class LineaReporte:
    """Una fila del reporte: un producto y lo que se vendió de él en el mes."""

    def __init__(self, producto, tipo, unidades, total):
        self.producto = producto
        self.tipo = tipo
        self.unidades = int(unidades)
        self.total = round(float(total), 2)

    @property
    def tipo_texto(self):
        return {"almuerzo": "Almuerzo", "tienda": "Producto de tienda"}.get(self.tipo, "Retirado")


class ReporteMensual:
    """Las ventas de un mes. Lo arma PedidoDAO.reporte_mensual() con una consulta SQL propia."""

    def __init__(self, anio, mes, lineas, pedidos_por_estado):
        self._anio, self._mes = self.validar_mes(anio, mes)
        self._lineas = list(lineas)
        # {"entregado": (cantidad de pedidos, dinero), "no_recogido": (...), ...}
        self._pedidos_por_estado = dict(pedidos_por_estado)

    # ---------- Validación ----------
    @staticmethod
    def validar_mes(anio, mes):
        try:
            anio, mes = int(anio), int(mes)
        except (TypeError, ValueError):
            raise DatosInvalidos("Elige un mes válido.") from None
        if not 1 <= mes <= 12:
            raise DatosInvalidos("El mes debe estar entre 1 y 12.")
        if not 2020 <= anio <= 2100:
            raise DatosInvalidos("Elige un año entre 2020 y 2100.")
        return anio, mes

    @classmethod
    def leer_mes(cls, texto):
        """'2026-11' (lo que envía <input type="month">) → (2026, 11)."""
        partes = (texto or "").strip().split("-")
        if len(partes) != 2:
            raise DatosInvalidos("Elige un mes válido, por ejemplo 2026-11.")
        return cls.validar_mes(*partes)

    @staticmethod
    def rango_fechas(anio, mes):
        """Primer día del mes y primer día del mes siguiente, como texto para comparar en SQL."""
        siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
        return f"{anio:04d}-{mes:02d}-01", f"{siguiente[0]:04d}-{siguiente[1]:02d}-01"

    # ---------- Datos ----------
    @property
    def anio(self):
        return self._anio

    @property
    def mes(self):
        return self._mes

    @property
    def clave(self):
        return f"{self._anio:04d}-{self._mes:02d}"

    @property
    def nombre(self):
        return f"{MESES[self._mes - 1].capitalize()} {self._anio}"

    @property
    def lineas(self):
        return list(self._lineas)

    @property
    def esta_vacio(self):
        return not self._lineas

    @property
    def total_vendido(self):
        return round(sum(linea.total for linea in self._lineas), 2)

    @property
    def unidades_vendidas(self):
        return sum(linea.unidades for linea in self._lineas)

    def pedidos(self, estado):
        """Cantidad de pedidos del mes en ese estado."""
        return self._pedidos_por_estado.get(estado, (0, 0.0))[0]

    def dinero(self, estado):
        """Dinero de los pedidos del mes en ese estado."""
        return round(self._pedidos_por_estado.get(estado, (0, 0.0))[1], 2)

    @property
    def total_pedidos(self):
        """Pedidos que cuentan como venta: todos menos los cancelados."""
        return sum(n for estado, (n, _) in self._pedidos_por_estado.items() if estado != "cancelado")

    # ---------- Exportar ----------
    def a_csv(self):
        """El reporte como texto CSV, listo para abrir en Excel."""
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow([f"Reporte de ventas - {self.nombre}"])
        escritor.writerow([])
        escritor.writerow(["Producto", "Tipo", "Unidades", "Total (US$)"])
        for linea in self._lineas:
            escritor.writerow([linea.producto, linea.tipo_texto, linea.unidades, f"{linea.total:.2f}"])
        escritor.writerow(["TOTAL", "", self.unidades_vendidas, f"{self.total_vendido:.2f}"])
        escritor.writerow([])
        escritor.writerow(["Pedidos", "Cantidad", "", "Total (US$)"])
        for estado, texto in (("entregado", "Entregados"), ("pendiente", "Pendientes de retiro"),
                              ("no_recogido", "No recogidos"), ("cancelado", "Cancelados")):
            escritor.writerow([texto, self.pedidos(estado), "", f"{self.dinero(estado):.2f}"])
        # El BOM (﻿) hace que Excel lea bien las tildes y la ñ.
        return "﻿" + salida.getvalue()
