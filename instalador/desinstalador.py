"""Desinstalador de Registro de Taxímetros para Windows."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import winreg
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

APP_ID = "RegistroTaximetros"
NOMBRE = "Registro de Taxímetros"
CLAVE_REGISTRO = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"


def directorio_por_defecto() -> Path:
    localappdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    return Path(localappdata) / "Programs" / APP_ID


def directorio_instalado() -> Path:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO) as clave:
            valor, _ = winreg.QueryValueEx(clave, "InstallLocation")
        return Path(valor)
    except OSError:
        return directorio_por_defecto()


def carpeta_escritorio() -> Path:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as clave:
            valor, _ = winreg.QueryValueEx(clave, "Desktop")
        return Path(os.path.expandvars(valor))
    except OSError:
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def carpeta_inicio() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / NOMBRE


def _comilla(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def quitar_accesos() -> None:
    inicio = carpeta_inicio()
    accesos = [
        inicio / f"{NOMBRE}.lnk",
        inicio / "Desinstalar.lnk",
        carpeta_escritorio() / f"{NOMBRE}.lnk",
    ]
    for acceso in accesos:
        try:
            acceso.unlink()
        except OSError:
            pass
    try:
        inicio.rmdir()
    except OSError:
        pass


def programar_borrado(destino: Path, borrar_datos: bool) -> None:
    ejecutable = destino / "RegistroTaximetros.exe"
    configuracion = destino / "actualizaciones.json"
    desinstalador = destino / "DesinstalarRegistroTaximetros.exe"

    lineas = [
        "$ErrorActionPreference = 'SilentlyContinue'",
        f"$pidActual = {os.getpid()}",
        "for ($i = 0; $i -lt 60; $i++) {",
        "    if (-not (Get-Process -Id $pidActual -ErrorAction SilentlyContinue)) { break }",
        "    Start-Sleep -Milliseconds 300",
        "}",
        "Start-Sleep -Milliseconds 300",
        f"Remove-Item -LiteralPath {_comilla(str(ejecutable))} -Force",
        f"Remove-Item -LiteralPath {_comilla(str(configuracion))} -Force",
        f"Remove-Item -LiteralPath {_comilla(str(desinstalador))} -Force",
    ]
    if borrar_datos:
        lineas.append(f"Remove-Item -LiteralPath {_comilla(str(destino))} -Recurse -Force")
    else:
        lineas.append(f"Remove-Item -LiteralPath {_comilla(str(destino))} -Force")
    lineas.append("Remove-Item -LiteralPath $PSCommandPath -Force")

    script = Path(tempfile.gettempdir()) / "desinstalar_registro_taximetros.ps1"
    script.write_text("\n".join(lineas), encoding="utf-8")
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def desinstalar(destino: Path, borrar_datos: bool = False) -> None:
    quitar_accesos()
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CLAVE_REGISTRO)
    except OSError:
        pass
    programar_borrado(destino, borrar_datos)


class DesinstaladorApp:
    def __init__(self, root: tk.Tk, destino: Path):
        self.root = root
        self.destino = destino
        self.root.title(f"Desinstalar {NOMBRE}")
        self.root.resizable(False, False)
        self.borrar_datos = tk.BooleanVar(value=False)
        self._crear_interfaz()

    def _crear_interfaz(self) -> None:
        marco = ttk.Frame(self.root, padding=18)
        marco.pack(fill="both", expand=True)
        ttk.Label(
            marco,
            text=f"Desinstalar {NOMBRE}",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(
            marco, text=f"Se quitará de:\n{self.destino}", foreground="#555555"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Checkbutton(
            marco,
            text="Eliminar también los registros de ventas guardados",
            variable=self.borrar_datos,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 16))
        botones = ttk.Frame(marco)
        botones.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(botones, text="Cancelar", command=self.root.destroy, width=12).pack(
            side="left", padx=6
        )
        ttk.Button(botones, text="Desinstalar", command=self.confirmar, width=14).pack(
            side="left"
        )

    def confirmar(self) -> None:
        if not messagebox.askyesno(
            "Confirmar",
            "¿Desinstalar la aplicación de este equipo?",
            parent=self.root,
        ):
            return
        try:
            desinstalar(self.destino, self.borrar_datos.get())
        except Exception as error:  # noqa: BLE001 - se muestra al usuario
            messagebox.showerror("Error", str(error), parent=self.root)
            return
        messagebox.showinfo(
            "Desinstalación iniciada",
            "La aplicación se quitará en unos segundos.",
            parent=self.root,
        )
        self.root.destroy()


def main() -> None:
    argumentos = sys.argv[1:]
    destino = directorio_instalado()
    borrar_datos = False
    if "--dir" in argumentos:
        indice = argumentos.index("--dir")
        if indice + 1 < len(argumentos):
            destino = Path(os.path.expandvars(argumentos[indice + 1]))
    if "--borrar-datos" in argumentos:
        borrar_datos = True

    if "--dir" in argumentos or "--borrar-datos" in argumentos:
        desinstalar(destino, borrar_datos)
        print(f"Desinstalación programada para: {destino}")
        return

    root = tk.Tk()
    DesinstaladorApp(root, destino)
    root.mainloop()


if __name__ == "__main__":
    main()
