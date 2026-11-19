"""Capa de acceso a datos (SQLite) para el registro de taxímetros vendidos."""

from __future__ import annotations

import csv
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date

from config import DB_PATH


@dataclass
class Venta:
    id: int | None
    fecha: str
    cliente: str
    numero_serie: str
    tipo_carro: str
    placas: str
    telefono: str


def _conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar() -> None:
    with closing(_conectar()) as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                cliente TEXT NOT NULL,
                numero_serie TEXT NOT NULL UNIQUE,
                tipo_carro TEXT NOT NULL,
                placas TEXT NOT NULL,
                telefono TEXT NOT NULL
            )
            """
        )
        conexion.execute("CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON ventas(cliente)")
        conexion.execute("CREATE INDEX IF NOT EXISTS idx_ventas_serie ON ventas(numero_serie)")
        conexion.execute("CREATE INDEX IF NOT EXISTS idx_ventas_placas ON ventas(placas)")
        conexion.commit()


def normalizar(venta: Venta) -> Venta:
    return Venta(
        id=venta.id,
        fecha=venta.fecha.strip(),
        cliente=" ".join(venta.cliente.split()),
        numero_serie=venta.numero_serie.strip().upper(),
        tipo_carro=" ".join(venta.tipo_carro.split()),
        placas=venta.placas.strip().upper(),
        telefono=venta.telefono.strip(),
    )


def validar(venta: Venta) -> Venta:
    venta = normalizar(venta)
    if not venta.cliente:
        raise ValueError("Ingresa el nombre del cliente.")
    if not venta.numero_serie:
        raise ValueError("Ingresa el número de serie del taxímetro.")
    if not venta.tipo_carro:
        raise ValueError("Ingresa el tipo de carro.")
    if not venta.placas:
        raise ValueError("Ingresa las placas del vehículo.")
    if not venta.telefono:
        raise ValueError("Ingresa el número de teléfono.")
    if len(re.sub(r"\D", "", venta.telefono)) < 7:
        raise ValueError("El teléfono debe tener al menos 7 dígitos.")
    try:
        date.fromisoformat(venta.fecha)
    except ValueError as exc:
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD.") from exc
    return venta


def listar_ventas(busqueda: str = "") -> list[Venta]:
    consulta = """
        SELECT id, fecha, cliente, numero_serie, tipo_carro, placas, telefono
        FROM ventas
    """
    parametros: tuple = ()
    if busqueda.strip():
        consulta += """
            WHERE cliente LIKE ? OR numero_serie LIKE ? OR tipo_carro LIKE ?
               OR placas LIKE ? OR telefono LIKE ? OR fecha LIKE ?
               OR CAST(id AS TEXT) LIKE ?
        """
        termino = f"%{busqueda.strip()}%"
        parametros = (termino,) * 7
    consulta += " ORDER BY fecha DESC, id DESC"
    with closing(_conectar()) as conexion:
        filas = conexion.execute(consulta, parametros).fetchall()
    return [Venta(*fila) for fila in filas]


def obtener(venta_id: int) -> Venta | None:
    with closing(_conectar()) as conexion:
        fila = conexion.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
    return Venta(*fila) if fila else None


def contar() -> int:
    with closing(_conectar()) as conexion:
        return int(conexion.execute("SELECT COUNT(*) FROM ventas").fetchone()[0])


def insertar(venta: Venta) -> int:
    with closing(_conectar()) as conexion:
        try:
            cursor = conexion.execute(
                """
                INSERT INTO ventas (fecha, cliente, numero_serie, tipo_carro, placas, telefono)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    venta.fecha,
                    venta.cliente,
                    venta.numero_serie,
                    venta.tipo_carro,
                    venta.placas,
                    venta.telefono,
                ),
            )
            conexion.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Ya existe una venta registrada con ese número de serie."
            ) from exc


def actualizar(venta: Venta) -> None:
    if venta.id is None:
        raise ValueError("No se indicó el registro a actualizar.")
    with closing(_conectar()) as conexion:
        try:
            conexion.execute(
                """
                UPDATE ventas
                SET fecha = ?, cliente = ?, numero_serie = ?, tipo_carro = ?, placas = ?, telefono = ?
                WHERE id = ?
                """,
                (
                    venta.fecha,
                    venta.cliente,
                    venta.numero_serie,
                    venta.tipo_carro,
                    venta.placas,
                    venta.telefono,
                    venta.id,
                ),
            )
            conexion.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Ya existe otra venta registrada con ese número de serie."
            ) from exc


def eliminar(venta_id: int) -> None:
    with closing(_conectar()) as conexion:
        conexion.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        conexion.commit()


def exportar_csv(ruta: str, ventas: list[Venta]) -> None:
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(
            ["ID", "Fecha", "Cliente", "Número de serie", "Tipo de carro", "Placas", "Teléfono"]
        )
        for venta in ventas:
            escritor.writerow(
                [
                    venta.id,
                    venta.fecha,
                    venta.cliente,
                    venta.numero_serie,
                    venta.tipo_carro,
                    venta.placas,
                    venta.telefono,
                ]
            )
