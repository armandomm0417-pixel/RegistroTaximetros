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
}


def load_update_config() -> dict[str, str]:
    configuracion = dict(UPDATE_DEFAULTS)
    archivo = app_dir() / "actualizaciones.json"
    if archivo.exists():
        try:
            with archivo.open(encoding="utf-8-sig") as manejador:
                datos = json.load(manejador)
            if isinstance(datos, dict):
                for clave in UPDATE_DEFAULTS:
                    valor = datos.get(clave)
                    if valor:
                        configuracion[clave] = str(valor).strip()
        except (OSError, ValueError):
            pass
    return configuracion


UPDATE_CONFIG = load_update_config()


def updates_configured() -> bool:
    return bool(UPDATE_CONFIG["owner"] and UPDATE_CONFIG["repo"])
