"""Configuración y rutas de la aplicación Registro de Taxímetros."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "RegistroTaximetros"
APP_TITLE = "Registro de Taxímetros Vendidos"


def is_frozen() -> bool:
    """Devuelve True cuando se ejecuta como .exe generado con PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Carpeta donde está el programa (o el .exe)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    """Ruta de archivos incluidos dentro del paquete PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / name
    return app_dir() / name


def data_dir() -> Path:
    """Carpeta de datos. Se usa LOCALAPPDATA si la carpeta del programa no permite escribir."""
    directorio = app_dir() / "datos"
    try:
        directorio.mkdir(parents=True, exist_ok=True)
        prueba = directorio / ".write_test"
        prueba.touch()
        prueba.unlink()
        return directorio
    except OSError:
        alternativa = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME / "datos"
        alternativa.mkdir(parents=True, exist_ok=True)
        return alternativa


DB_PATH = data_dir() / "ventas.sqlite3"


def _load_version() -> str:
    try:
        with resource_path("version.json").open(encoding="utf-8") as archivo:
            return str(json.load(archivo).get("version", "1.0.0"))
    except (OSError, ValueError, AttributeError):
        return "1.0.0"


APP_VERSION = _load_version()

# Valores por defecto. Se pueden sobrescribir con actualizaciones.json junto al programa.
UPDATE_DEFAULTS = {
    "owner": "",
    "repo": "",
    "asset_name": "RegistroTaximetros.exe",
    "auto_check": True,
    "check_interval_minutes": 60,
}


def _normalizar_updates(datos: dict) -> dict:
    """Convierte los valores leídos del JSON a los tipos esperados."""
    configuracion = dict(UPDATE_DEFAULTS)
    if not isinstance(datos, dict):
        return configuracion

    for clave, por_defecto in UPDATE_DEFAULTS.items():
        if clave not in datos:
            continue
        valor = datos[clave]
        if isinstance(por_defecto, bool):
            if isinstance(valor, bool):
                configuracion[clave] = valor
            elif isinstance(valor, str):
                configuracion[clave] = valor.strip().lower() in {
                    "1", "true", "sí", "si", "yes", "on", "activado"
                }
            elif isinstance(valor, (int, float)):
                configuracion[clave] = bool(valor)
        elif isinstance(por_defecto, int):
            try:
                numero = int(str(valor).strip())
            except (TypeError, ValueError):
                continue
            configuracion[clave] = max(1, min(numero, 1440))
        else:
            texto = "" if valor is None else str(valor).strip()
            if texto:
                configuracion[clave] = texto
    return configuracion


def load_update_config() -> dict:
    archivo = app_dir() / "actualizaciones.json"
    if archivo.exists():
        try:
            with archivo.open(encoding="utf-8-sig") as manejador:
                return _normalizar_updates(json.load(manejador))
        except (OSError, ValueError):
            pass
    return dict(UPDATE_DEFAULTS)


UPDATE_CONFIG = load_update_config()


def guardar_update_config(datos: dict) -> dict:
    """Guarda la configuración y actualiza el dict compartido con el actualizador."""
    configuracion = _normalizar_updates(datos)
    archivo = app_dir() / "actualizaciones.json"
    with archivo.open("w", encoding="utf-8") as manejador:
        json.dump(configuracion, manejador, indent=2, ensure_ascii=False)
        manejador.write("\n")
    UPDATE_CONFIG.clear()
    UPDATE_CONFIG.update(configuracion)
    return configuracion


def updates_configured() -> bool:
    return bool(UPDATE_CONFIG["owner"] and UPDATE_CONFIG["repo"])
