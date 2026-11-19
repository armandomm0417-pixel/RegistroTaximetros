"""Sistema de actualizaciones automáticas mediante GitHub Releases."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from config import (
    APP_NAME,
    APP_VERSION,
    UPDATE_CONFIG,
    data_dir,
    is_frozen,
)

USER_AGENT = f"{APP_NAME}/{APP_VERSION} (actualizador)"
TIMEOUT = 10


@dataclass
class UpdateInfo:
    available: bool
    version: str = ""
    notes: str = ""
    url: str = ""
    asset_name: str = ""
    asset_url: str = ""
    assets: list[dict] | None = None


def parse_version(texto: str) -> tuple[int, int, int]:
    coincidencia = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(texto))
    if not coincidencia:
        return (0, 0, 0)
    return tuple(int(parte or 0) for parte in coincidencia.groups())


def _url_api() -> str:
    return (
        f"https://api.github.com/repos/{UPDATE_CONFIG['owner']}/"
        f"{UPDATE_CONFIG['repo']}/releases/latest"
    )


def descargar_json(url: str) -> dict:
    peticion = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def check() -> UpdateInfo:
    """Consulta la última release publicada en GitHub."""
    datos = descargar_json(_url_api())
    version = str(datos.get("tag_name", "")).lstrip("vV")
    activa = parse_version(version) > parse_version(APP_VERSION)
    nombre_asset = UPDATE_CONFIG["asset_name"]
    assets = datos.get("assets", []) or []
    asset = next((a for a in assets if a.get("name") == nombre_asset), None)
    if activa and asset is None:
        raise RuntimeError(
            f"La versión {version} no incluye el archivo {nombre_asset}."
        )
    return UpdateInfo(
        available=activa,
        version=version,
        notes=str(datos.get("body", "") or "").strip(),
        url=str(datos.get("html_url", "") or ""),
        asset_name=nombre_asset,
        asset_url=str(asset.get("browser_download_url", "")) if asset else "",
        assets=assets,
    )


def descargar(info: UpdateInfo, progreso=None) -> Path:
    """Descarga el ejecutable de la nueva versión y verifica su SHA256 si existe."""
    if not info.asset_url:
        raise RuntimeError("La release no contiene un archivo descargable.")

    destino_dir = data_dir() / "actualizaciones"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / info.asset_name
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

    _verificar_sha256(temporal, info)
    temporal.replace(destino)
    return destino


def _verificar_sha256(archivo: Path, info: UpdateInfo) -> None:
    nombre_checksum = f"{info.asset_name}.sha256"
    checksum = next((a for a in (info.assets or []) if a.get("name") == nombre_checksum), None)
    if checksum is None:
        return

    peticion = urllib.request.Request(
        checksum["browser_download_url"], headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
        contenido = respuesta.read().decode("utf-8", errors="replace")
    esperado = contenido.split()[0].strip().lower() if contenido.split() else ""

    hash_calculado = hashlib.sha256()
    with archivo.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            hash_calculado.update(bloque)
    real = hash_calculado.hexdigest()

    if esperado and esperado != real:
        archivo.unlink(missing_ok=True)
        raise RuntimeError("La suma de verificación SHA256 no coincide. No se instaló nada.")


def _ps_quote(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def instalar(archivo: Path) -> None:
    """Reemplaza el ejecutable actual y reinicia la aplicación (solo en modo .exe)."""
    if not is_frozen():
        raise RuntimeError("La instalación automática solo está disponible en el ejecutable .exe.")

    actual = Path(sys.executable).resolve()
    registro = data_dir() / "actualizacion.log"
    script = f"""$ErrorActionPreference = 'Stop'
$pidActual = {os.getpid()}
$origen = {_ps_quote(str(archivo.resolve()))}
$destino = {_ps_quote(str(actual))}
$registro = {_ps_quote(str(registro))}
$padre = $null
try {{
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pidActual" -ErrorAction SilentlyContinue
    if ($proc) {{ $padre = $proc.ParentProcessId }}
}} catch {{}}

try {{
    for ($i = 0; $i -lt 60; $i++) {{
        $vivo = (Get-Process -Id $pidActual -ErrorAction SilentlyContinue) -ne $null
        if ($padre) {{ $vivo = $vivo -or ((Get-Process -Id $padre -ErrorAction SilentlyContinue) -ne $null) }}
        if (-not $vivo) {{ break }}
        Start-Sleep -Milliseconds 500
    }}
    Start-Sleep -Milliseconds 600
    $copiado = $false
    for ($i = 0; $i -lt 10; $i++) {{
        try {{
            Copy-Item -LiteralPath $origen -Destination $destino -Force -ErrorAction Stop
            $copiado = $true
            break
        }} catch {{
            Start-Sleep -Milliseconds 700
        }}
    }}
    if (-not $copiado) {{ throw 'No se pudo reemplazar el ejecutable; comprueba que no haya otra instancia abierta.' }}
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
