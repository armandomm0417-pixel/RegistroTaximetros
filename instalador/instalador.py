"""Instalador de Registro de Taxímetros para Windows (sin dependencias externas)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_ID = "RegistroTaximetros"
NOMBRE = "Registro de Taxímetros"
VERSION = "1.0.1"


def recurso(nombre: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / nombre
    return Path(__file__).resolve().parent / nombre


def directorio_por_defecto() -> Path:
    localappdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    return Path(localappdata) / "Programs" / APP_ID


def carpeta_escritorio() -> Path:
    try:
        clave = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        valor, _ = winreg.QueryValueEx(clave, "Desktop")
        winreg.CloseKey(clave)
        return Path(os.path.expandvars(valor))
    except OSError:
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def carpeta_inicio() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / NOMBRE


def _comilla(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def crear_acceso_directo(ruta_lnk: Path, destino: Path, directorio: Path) -> None:
    ruta_lnk.parent.mkdir(parents=True, exist_ok=True)
    comando = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
        f"{_comilla(str(ruta_lnk))}); "
        f"$s.TargetPath={_comilla(str(destino))}; "
        f"$s.WorkingDirectory={_comilla(str(directorio))}; "
        f"$s.IconLocation={_comilla(str(destino) + ',0')}; $s.Save()"
    )
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-Command",
            comando,
        ],
        check=True,
        capture_output=True,
    )


def registrar_desinstalador(destino: Path, ejecutable: Path, desinstalador: Path) -> None:
    ruta = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ruta) as clave:
        winreg.SetValueEx(clave, "DisplayName", 0, winreg.REG_SZ, NOMBRE)
        winreg.SetValueEx(clave, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(clave, "Publisher", 0, winreg.REG_SZ, APP_ID)
        winreg.SetValueEx(clave, "InstallLocation", 0, winreg.REG_SZ, str(destino))
        winreg.SetValueEx(
            clave, "UninstallString", 0, winreg.REG_SZ, f'"{desinstalador}"'
        )
        winreg.SetValueEx(
            clave, "DisplayIcon", 0, winreg.REG_SZ, f"{ejecutable},0"
        )
        winreg.SetValueEx(clave, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(clave, "NoRepair", 0, winreg.REG_DWORD, 1)


def instalar(
    destino_texto: str,
    crear_escritorio: bool = True,
    crear_inicio: bool = True,
    ejecutar: bool = False,
) -> Path:
    destino = Path(os.path.expandvars(str(destino_texto).strip()))
    if not destino_texto.strip():
        raise ValueError("Indica la carpeta de instalación.")
    destino.mkdir(parents=True, exist_ok=True)

    ejecutable = destino / "RegistroTaximetros.exe"
    configuracion = destino / "actualizaciones.json"
    desinstalador = destino / "DesinstalarRegistroTaximetros.exe"

    archivos = (
        ("RegistroTaximetros.exe", ejecutable),
        ("actualizaciones.json", configuracion),
        ("DesinstalarRegistroTaximetros.exe", desinstalador),
    )
    for nombre, ruta_destino in archivos:
        try:
            shutil.copy2(recurso(nombre), ruta_destino)
        except PermissionError as error:
            raise RuntimeError(
                f"No se pudo reemplazar {ruta_destino.name}. "
                "Cierra el programa si está abierto e inténtalo de nuevo."
            ) from error

    if crear_inicio:
        inicio = carpeta_inicio()
        crear_acceso_directo(inicio / f"{NOMBRE}.lnk", ejecutable, destino)
        crear_acceso_directo(inicio / "Desinstalar.lnk", desinstalador, destino)

    if crear_escritorio:
        crear_acceso_directo(
            carpeta_escritorio() / f"{NOMBRE}.lnk", ejecutable, destino
        )

    registrar_desinstalador(destino, ejecutable, desinstalador)

    if ejecutar:
        subprocess.Popen([str(ejecutable)], cwd=str(destino))
    return destino


class InstaladorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Instalar {NOMBRE} v{VERSION}")
        self.root.resizable(False, False)
        self.ruta = tk.StringVar(value=str(directorio_por_defecto()))
        self.escritorio = tk.BooleanVar(value=True)
        self.inicio = tk.BooleanVar(value=True)
        self.ejecutar = tk.BooleanVar(value=True)
        self._crear_interfaz()

    def _crear_interfaz(self) -> None:
        marco = ttk.Frame(self.root, padding=16)
        marco.pack(fill="both", expand=True)

        ttk.Label(
            marco, text=f"Instalar {NOMBRE}", font=("Segoe UI", 15, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(
            marco,
            text="El programa se instalará para tu usuario. No necesitas permisos de administrador.",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        ttk.Label(marco, text="Carpeta de instalación:").grid(
            row=2, column=0, columnspan=3, sticky="w"
        )
        ttk.Entry(marco, textvariable=self.ruta, width=54).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 10)
        )
        ttk.Button(marco, text="Examinar...", command=self.examinar, width=14).grid(
            row=3, column=2, padx=(8, 0), pady=(4, 10)
        )

        ttk.Checkbutton(
            marco, text="Crear acceso directo en el escritorio", variable=self.escritorio
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Checkbutton(
            marco, text="Crear acceso en el menú Inicio", variable=self.inicio
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Checkbutton(
            marco, text="Abrir la aplicación al terminar", variable=self.ejecutar
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=2)

        self.estado = ttk.Label(marco, text="", foreground="#0B5FA5")
        self.estado.grid(row=7, column=0, columnspan=3, sticky="w", pady=(14, 6))

        botones = ttk.Frame(marco)
        botones.grid(row=8, column=0, columnspan=3, sticky="e")
        ttk.Button(botones, text="Cancelar", command=self.root.destroy, width=12).pack(
            side="left", padx=6
        )
        self.boton_instalar = ttk.Button(
            botones, text="Instalar", command=self.instalar, width=14
        )
        self.boton_instalar.pack(side="left")

    def examinar(self) -> None:
        seleccion = filedialog.askdirectory(
            parent=self.root, title="Carpeta de instalación", initialdir=self.ruta.get()
        )
        if seleccion:
            self.ruta.set(seleccion)

    def instalar(self) -> None:
        self.boton_instalar.config(state="disabled")
        self.estado.config(text="Instalando...")
        self.root.update_idletasks()
        try:
            destino = instalar(
                self.ruta.get(),
                crear_escritorio=self.escritorio.get(),
                crear_inicio=self.inicio.get(),
                ejecutar=self.ejecutar.get(),
            )
        except Exception as error:  # noqa: BLE001 - se muestra al usuario
            self.boton_instalar.config(state="normal")
            self.estado.config(text="")
            messagebox.showerror("No se pudo instalar", str(error), parent=self.root)
            return
        messagebox.showinfo(
            "Instalación completada",
            f"{NOMBRE} se instaló en:\n{destino}\n\n"
            "Puedes desinstalarlo desde el menú Inicio o desde "
            "Aplicaciones y características.",
            parent=self.root,
        )
        self.root.destroy()


def main() -> None:
    argumentos = sys.argv[1:]
    silencioso = "--silencioso" in argumentos
    sin_accesos = "--sin-accesos" in argumentos

    destino_texto = ""
    if "--dir" in argumentos:
        indice = argumentos.index("--dir")
        if indice + 1 >= len(argumentos):
            print("Uso: InstalarRegistroTaximetros.exe --dir \"C:\\Ruta\"")
            sys.exit(1)
        destino_texto = argumentos[indice + 1]
    elif silencioso or sin_accesos:
        destino_texto = str(directorio_por_defecto())

    if destino_texto:
        try:
            destino = instalar(
                destino_texto,
                crear_escritorio=not sin_accesos,
                crear_inicio=not sin_accesos,
                ejecutar=False,
            )
        except Exception as error:  # noqa: BLE001
            print(f"Error: {error}")
            sys.exit(1)
        print(f"Instalado en: {destino}")
        return

    root = tk.Tk()
    InstaladorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
