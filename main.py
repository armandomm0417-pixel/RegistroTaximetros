"""Punto de entrada de la aplicación Registro de Taxímetros."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import database
from ui import RegistroApp


def main() -> None:
    # Permite que la interfaz se vea nítida en pantallas con escalado en Windows.
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass

    try:
        database.inicializar()
    except Exception as error:  # noqa: BLE001 - error crítico al iniciar
        messagebox.showerror(
            "Error de inicio", f"No se pudo abrir la base de datos:\n{error}"
        )
        return

    root = tk.Tk()
    RegistroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
