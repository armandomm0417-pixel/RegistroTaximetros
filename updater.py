"""Sistema de actualizaciones automáticas mediante un archivo latest.json."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from config import APP_NAME, APP_VERSION, UPDATE_CONFIG, data_dir, is_frozen

USER_AGENT = f"{APP_NAME}/{APP_VERSION} (actualizador)"
TIMEOUT = 20


@dataclass
class UpdateInfo:
    available: bool
    version: str = ""
    notes: str = ""
    url: str = ""
    asset_name: str = ""
    asset_url: str = ""
    sha256: str = ""


def parse_version(texto: str) -> tuple[int, int, int]:
    coincidencia = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(texto))
    if not coincidencia:
        return (0, 0, 0)
    return tuple(int(parte or 0) for parte in coincidencia.groups())


def latest_json_url() -> str:
    """Devuelve la URL de latest.json (propia o construida desde GitHub)."""
    personalizada = str(UPDATE_CONFIG.get("latest_url", "") or "").strip()
    if personalizada:
        return personalizada
    return (
        f"https://github.com/{UPDATE_CONFIG['owner']}/"
        f"{UPDATE_CONFIG['repo']}/releases/latest/download/latest.json"
    )


def descargar_json(url: str) -> dict:
    peticion = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def check() -> UpdateInfo:
    """Lee latest.json y determina si hay una versión nueva."""
    url = latest_json_url()
    datos = descargar_json(url)
    version = str(datos.get("version") or datos.get("tag_name") or "").lstrip("vV")
    nombre_o_url = str(datos.get("url") or "").strip()
    if not nombre_o_url:
        raise RuntimeError("latest.json no indica el instalador en el campo 'url'.")

    asset_url = urllib.parse.urljoin(url, nombre_o_url)
    nombre = urllib.parse.unquote(urllib.parse.urlparse(asset_url).path.rsplit("/", 1)[-1])
    if not nombre:
        nombre = UPDATE_CONFIG.get("asset_name") or "RegistroTaximetrosSetup.exe"

    return UpdateInfo(
        available=parse_version(version) > parse_version(APP_VERSION),
        version=version,
        notes=str(datos.get("notes") or datos.get("body") or "").strip(),
        url=nombre_o_url,
        asset_name=nombre,
        asset_url=asset_url,
        sha256=str(datos.get("sha256") or "").strip(),
    )


def directorio_descargas() -> Path:
    directorio = data_dir() / "actualizaciones"
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def ruta_pendiente() -> Path:
    return directorio_descargas() / "pendiente.json"


def leer_pendiente() -> dict | None:
    try:
        datos = json.loads(ruta_pendiente().read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else None
    except (OSError, ValueError):
        return None


def guardar_pendiente(info: UpdateInfo, archivo: Path) -> None:
    datos = {
        "version": info.version,
        "archivo": archivo.name,
        "notes": info.notes,
        "sha256": info.sha256,
    }
    ruta_pendiente().write_text(
        json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def borrar_pendiente() -> None:
    ruta_pendiente().unlink(missing_ok=True)


def descargar(info: UpdateInfo, progreso=None) -> Path:
    """Descarga el instalador en segundo plano y verifica su SHA256."""
    if not info.asset_url:
        raise RuntimeError("latest.json no contiene una URL de descarga válida.")
    if not info.sha256:
        raise RuntimeError("latest.json no incluye el SHA256 del instalador.")

    destino = directorio_descargas() / info.asset_name
    temporal = destino.with_suffix(destino.suffix + ".part")

    peticion = urllib.request.Request(info.asset_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta, temporal.open("wb") as archivo:
        total = int(respuesta.headers.get("Content-Length") or 0)
        descargado = 0
        while True:
            bloque = respuesta.read(64 * 1024)
            if not bloque:
                break
            archivo.write(bloque)
            descargado += len(bloque)
            if progreso:
                progreso(descargado, total)

    _verificar_sha256(temporal, info.sha256)
    temporal.replace(destino)
    guardar_pendiente(info, destino)
    return destino


def _verificar_sha256(archivo: Path, esperado: str) -> None:
    esperado = esperado.strip().lower()
    hash_calculado = hashlib.sha256()
    with archivo.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            hash_calculado.update(bloque)
    real = hash_calculado.hexdigest()
    if real != esperado:
        archivo.unlink(missing_ok=True)
        raise RuntimeError("La suma SHA256 no coincide. No se instaló nada.")


def _ps_quote(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def instalar(archivo: Path) -> None:
    """Cierra la app, ejecuta el instalador descargado y vuelve a abrirla."""
    if not is_frozen():
        raise RuntimeError("La instalación automática solo está disponible en el ejecutable .exe.")

    actual = Path(sys.executable).resolve()
    directorio = actual.parent
    registro = data_dir() / "actualizacion.log"
    borrar_pendiente()
    script = f"""$ErrorActionPreference = 'Stop'
$pidActual = {os.getpid()}
$instalador = {_ps_quote(str(archivo.resolve()))}
$directorio = {_ps_quote(str(directorio))}
$destino = {_ps_quote(str(actual))}
$registro = {_ps_quote(str(registro))}

try {{
    for ($i = 0; $i -lt 60; $i++) {{
        if (-not (Get-Process -Id $pidActual -ErrorAction SilentlyContinue)) {{ break }}
        Start-Sleep -Milliseconds 500
    }}
    Start-Sleep -Milliseconds 600
    $argumentos = '--dir \"' + $directorio + '\" --silencioso'
    Start-Process -FilePath $instalador -ArgumentList $argumentos -Wait
    Start-Process -FilePath $destino
}} catch {{
    Add-Content -LiteralPath $registro -Value ((Get-Date).ToString() + ' ' + $_.Exception.Message)
}}
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
"""
    temporal = Path(tempfile.gettempdir()) / f"actualizar_{APP_NAME}.ps1"
    temporal.write_text(script, encoding="utf-8")
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(temporal),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def abrir_releases() -> None:
    webbrowser.open(
        f"https://github.com/{UPDATE_CONFIG['owner']}/{UPDATE_CONFIG['repo']}/releases"
    )


def mostrar_carpeta(archivo: Path) -> None:
    subprocess.Popen(["explorer", "/select,", str(archivo)])
