"""Interfaz gráfica del registro de taxímetros vendidos."""

from __future__ import annotations

import queue
import threading
from datetime import date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database
import updater
from config import APP_TITLE, APP_VERSION, is_frozen, updates_configured

TIPOS_CARRO = (
    "Sedán",
    "SUV",
    "Hatchback",
    "Pickup",
    "Camioneta",
    "Van",
    "Mototaxi",
    "Otro",
)

COLUMNAS = (
    ("id", "ID", 60),
    ("fecha", "Fecha", 110),
    ("cliente", "Cliente", 220),
    ("numero_serie", "N.º de serie", 170),
    ("tipo_carro", "Tipo de carro", 140),
    ("placas", "Placas", 120),
    ("telefono", "Teléfono", 140),
)


class ProgressDialog(tk.Toplevel):
    """Ventana pequeña que muestra el avance de la descarga."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Descargando actualización")
        self.transient(parent)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        ttk.Label(
            self, text="Descargando la nueva versión...", padding=(18, 14, 18, 4)
        ).pack()
        self.barra = ttk.Progressbar(
            self, orient="horizontal", mode="determinate", length=360, maximum=100
        )
        self.barra.pack(padx=18, pady=6)
        self.etiqueta = ttk.Label(self, text="0 %")
        self.etiqueta.pack(pady=(0, 16))

        self.grab_set()
        self.update_idletasks()

    def actualizar(self, fraccion: float) -> None:
        porcentaje = max(0.0, min(1.0, fraccion)) * 100
        self.barra["value"] = porcentaje
        self.etiqueta.config(text=f"{porcentaje:.0f} %")


class RegistroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1010x650")
        self.root.minsize(930, 580)

        self.editing_id: int | None = None
        self.colas = queue.Queue()
        self.progreso: ProgressDialog | None = None

        self.vars = {
            "cliente": tk.StringVar(),
            "numero_serie": tk.StringVar(),
            "tipo_carro": tk.StringVar(),
            "placas": tk.StringVar(),
            "telefono": tk.StringVar(),
            "fecha": tk.StringVar(value=date.today().isoformat()),
            "busqueda": tk.StringVar(),
        }

        self._configurar_estilo()
        self._crear_menu()
        self._crear_interfaz()
        self.refrescar()
        self._poll()
        self.root.after(1200, lambda: self.verificar_actualizaciones(manual=False))

    # ------------------------------------------------------------------ UI

    def _configurar_estilo(self) -> None:
        estilo = ttk.Style()
        estilo.configure(".", font=("Segoe UI", 10))
        estilo.configure("Treeview", rowheight=26)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 14, "bold"))

    def _crear_menu(self) -> None:
        barra = tk.Menu(self.root)
        archivo = tk.Menu(barra, tearoff=0)
        archivo.add_command(label="Exportar CSV...", command=self.exportar_csv)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.root.destroy)
        ayuda = tk.Menu(barra, tearoff=0)
        ayuda.add_command(
            label="Buscar actualizaciones",
            command=lambda: self.verificar_actualizaciones(manual=True),
        )
        ayuda.add_command(label="Acerca de...", command=self.acerca_de)
        barra.add_cascade(label="Archivo", menu=archivo)
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.root.config(menu=barra)

    def _crear_interfaz(self) -> None:
        principal = ttk.Frame(self.root, padding=(12, 10))
        principal.pack(fill="both", expand=True)
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(2, weight=1)

        encabezado = ttk.Frame(principal)
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(encabezado, text="Registro de Taxímetros Vendidos", style="Titulo.TLabel").pack(
            side="left"
        )
        ttk.Label(
            encabezado, text=f"Versión {APP_VERSION}", foreground="#666666"
        ).pack(side="left", padx=(10, 0), pady=(6, 0))

        formulario = ttk.LabelFrame(principal, text="Datos de la venta", padding=10)
        formulario.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for columna in (1, 3):
            formulario.columnconfigure(columna, weight=1)

        self._campo(formulario, 0, 0, "cliente", "Nombre del cliente:")
        self._campo(formulario, 0, 2, "numero_serie", "N.º de serie del taxímetro:")
        self._campo(formulario, 1, 0, "tipo_carro", "Tipo de carro:", combo=True)
        self._campo(formulario, 1, 2, "placas", "Placas:")
        self._campo(formulario, 2, 0, "telefono", "Teléfono:")
        self._campo(formulario, 2, 2, "fecha", "Fecha de venta (AAAA-MM-DD):")

        botones_form = ttk.Frame(formulario)
        botones_form.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.boton_guardar = ttk.Button(
            botones_form, text="Guardar registro", command=self.guardar, width=20
        )
        self.boton_guardar.pack(side="left")
        ttk.Button(botones_form, text="Limpiar", command=self.limpiar, width=14).pack(
            side="left", padx=8
        )
        self.etiqueta_edicion = ttk.Label(botones_form, text="", foreground="#0B5FA5")
        self.etiqueta_edicion.pack(side="left", padx=10)

        busqueda = ttk.Frame(principal)
        busqueda.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(busqueda, text="Buscar:").pack(side="left")
        entrada_busqueda = ttk.Entry(busqueda, textvariable=self.vars["busqueda"], width=38)
        entrada_busqueda.pack(side="left", padx=(8, 8))
        entrada_busqueda.bind("<Return>", lambda _evento: self.refrescar())
        ttk.Button(busqueda, text="Buscar", command=self.refrescar, width=12).pack(side="left")
        ttk.Button(
            busqueda, text="Mostrar todos", command=self.mostrar_todos, width=14
        ).pack(side="left", padx=6)
        ttk.Button(
            busqueda, text="Exportar CSV", command=self.exportar_csv, width=16
        ).pack(side="right")

        marco_tabla = ttk.Frame(principal)
        marco_tabla.grid(row=3, column=0, sticky="nsew")
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            marco_tabla,
            columns=[columna[0] for columna in COLUMNAS],
            show="headings",
            selectmode="browse",
            height=12,
        )
        for clave, titulo, ancho in COLUMNAS:
            self.tree.heading(clave, text=titulo)
            self.tree.column(clave, width=ancho, anchor="w", stretch=(clave == "cliente"))
        self.tree.tag_configure("impar", background="#F4F6F9")
        self.tree.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self.tree.bind("<Double-1>", lambda _evento: self.editar_seleccion())

        vertical = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(marco_tabla, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        acciones = ttk.Frame(principal)
        acciones.grid(row=4, column=0, sticky="ew", pady=(8, 4))
        self.boton_editar = ttk.Button(
            acciones, text="Editar selección", command=self.editar_seleccion, state="disabled"
        )
        self.boton_editar.pack(side="left")
        self.boton_eliminar = ttk.Button(
            acciones,
            text="Eliminar selección",
            command=self.eliminar_seleccion,
            state="disabled",
        )
        self.boton_eliminar.pack(side="left", padx=8)
        ttk.Button(acciones, text="Salir", command=self.root.destroy).pack(side="right")

        barra_estado = ttk.Frame(principal)
        barra_estado.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        self.etiqueta_estado = ttk.Label(barra_estado, text="Listo.", anchor="w")
        self.etiqueta_estado.pack(side="left", fill="x", expand=True)
        self.etiqueta_total = ttk.Label(barra_estado, text="0 registros", anchor="e")
        self.etiqueta_total.pack(side="right")

    def _campo(
        self,
        padre: ttk.Widget,
        fila: int,
        columna: int,
        clave: str,
        texto: str,
        combo: bool = False,
    ) -> None:
        ttk.Label(padre, text=texto).grid(
            row=fila, column=columna, sticky="w", padx=(0, 6), pady=5
        )
        if combo:
            widget = ttk.Combobox(
                padre, textvariable=self.vars[clave], values=TIPOS_CARRO, width=24
            )
        else:
            widget = ttk.Entry(padre, textvariable=self.vars[clave], width=28)
        widget.grid(row=fila, column=columna + 1, sticky="ew", padx=(0, 18), pady=5)

    # ------------------------------------------------------------ Operaciones

    def _estado(self, mensaje: str) -> None:
        self.etiqueta_estado.config(text=mensaje)

    def refrescar(self) -> None:
        terminos = self.vars["busqueda"].get().strip()
        ventas = database.listar_ventas(terminos)
        self.tree.delete(*self.tree.get_children())
        for indice, venta in enumerate(ventas):
            self.tree.insert(
                "",
                "end",
                iid=str(venta.id),
                values=(
                    venta.id,
                    venta.fecha,
                    venta.cliente,
                    venta.numero_serie,
                    venta.tipo_carro,
                    venta.placas,
                    venta.telefono,
                ),
                tags=("impar",) if indice % 2 else (),
            )
        total = database.contar()
        texto = f"{len(ventas)} registro(s)"
        if terminos:
            texto += f" de {total} en total"
        self.etiqueta_total.config(text=texto)

    def mostrar_todos(self) -> None:
        self.vars["busqueda"].set("")
        self.refrescar()

    def _datos_formulario(self) -> database.Venta:
        return database.Venta(
            id=self.editing_id,
            fecha=self.vars["fecha"].get(),
            cliente=self.vars["cliente"].get(),
            numero_serie=self.vars["numero_serie"].get(),
            tipo_carro=self.vars["tipo_carro"].get(),
            placas=self.vars["placas"].get(),
            telefono=self.vars["telefono"].get(),
        )

    def guardar(self) -> None:
        try:
            venta = database.validar(self._datos_formulario())
        except ValueError as error:
            messagebox.showwarning("Revisa los datos", str(error), parent=self.root)
            return

        try:
            if self.editing_id is None:
                identificador = database.insertar(venta)
                mensaje = f"Venta guardada con el ID #{identificador}."
            else:
                database.actualizar(venta)
                mensaje = f"Registro #{self.editing_id} actualizado."
        except ValueError as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self.root)
            return

        self.limpiar()
        self.refrescar()
        self._estado(mensaje)

    def limpiar(self) -> None:
        for clave in ("cliente", "numero_serie", "tipo_carro", "placas", "telefono"):
            self.vars[clave].set("")
        self.vars["fecha"].set(date.today().isoformat())
        self.editing_id = None
        self.boton_guardar.config(text="Guardar registro")
        self.etiqueta_edicion.config(text="")

    def _al_seleccionar(self, _evento=None) -> None:
        hay_seleccion = bool(self.tree.selection())
        estado = "normal" if hay_seleccion else "disabled"
        self.boton_editar.config(state=estado)
        self.boton_eliminar.config(state=estado)

    def editar_seleccion(self) -> None:
        seleccion = self.tree.selection()
        if not seleccion:
            return
        venta = database.obtener(int(seleccion[0]))
        if venta is None:
            return
        self.vars["cliente"].set(venta.cliente)
        self.vars["numero_serie"].set(venta.numero_serie)
        self.vars["tipo_carro"].set(venta.tipo_carro)
        self.vars["placas"].set(venta.placas)
        self.vars["telefono"].set(venta.telefono)
        self.vars["fecha"].set(venta.fecha)
        self.editing_id = venta.id
        self.boton_guardar.config(text="Guardar cambios")
        self.etiqueta_edicion.config(text=f"Editando registro #{venta.id}")
        self._estado("Registro cargado en el formulario. Modifícalo y guarda los cambios.")

    def eliminar_seleccion(self) -> None:
        seleccion = self.tree.selection()
        if not seleccion:
            return
        venta_id = int(seleccion[0])
        aceptado = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar el registro #{venta_id}? Esta acción no se puede deshacer.",
            parent=self.root,
        )
        if not aceptado:
            return
        database.eliminar(venta_id)
        if self.editing_id == venta_id:
            self.limpiar()
        self.refrescar()
        self._estado(f"Registro #{venta_id} eliminado.")

    def exportar_csv(self) -> None:
        ventas = database.listar_ventas(self.vars["busqueda"].get().strip())
        if not ventas:
            messagebox.showinfo("Exportar CSV", "No hay registros para exportar.", parent=self.root)
            return
        ruta = filedialog.asksaveasfilename(
            parent=self.root,
            title="Guardar registros como CSV",
            defaultextension=".csv",
            initialfile="taximetros_vendidos.csv",
            filetypes=(("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")),
        )
        if not ruta:
            return
        try:
            database.exportar_csv(ruta, ventas)
        except OSError as error:
            messagebox.showerror("Error al exportar", str(error), parent=self.root)
            return
        self._estado(f"Se exportaron {len(ventas)} registro(s) a {ruta}")

    def acerca_de(self) -> None:
        estado = (
            "Configurado" if updates_configured() else "Sin configurar (el registro funciona igual)"
        )
        messagebox.showinfo(
            "Acerca de",
            f"{APP_TITLE}\nVersión {APP_VERSION}\n\n"
            f"Base de datos: {database.DB_PATH}\n"
            f"Actualizaciones: {estado}\n\n"
            "Los datos se guardan localmente y no se envían a ningún servidor.",
            parent=self.root,
        )

    # ------------------------------------------------------- Actualizaciones

    def verificar_actualizaciones(self, manual: bool = False) -> None:
        if not updates_configured():
            if manual:
                messagebox.showinfo(
                    "Actualizaciones",
                    "El sistema de actualizaciones todavía no está configurado.\n\n"
                    "Copia el archivo actualizaciones.example.json como "
                    "actualizaciones.json junto al programa y completa tu usuario "
                    "y nombre de repositorio de GitHub.\n\n"
                    "El registro de ventas funciona normalmente sin esta configuración.",
                    parent=self.root,
                )
            return
        self._estado("Comprobando actualizaciones en GitHub...")
        hilo = threading.Thread(target=self._verificar_worker, args=(manual,), daemon=True)
        hilo.start()

    def _verificar_worker(self, manual: bool) -> None:
        try:
            informacion = updater.check()
            self.colas.put(("check", informacion, manual))
        except Exception as error:  # noqa: BLE001 - se informa al usuario
            self.colas.put(("error_check", str(error), manual))

    def _descargar(self, informacion: updater.UpdateInfo) -> None:
        self.progreso = ProgressDialog(self.root)
        hilo = threading.Thread(
            target=self._descargar_worker, args=(informacion,), daemon=True
        )
        hilo.start()

    def _descargar_worker(self, informacion: updater.UpdateInfo) -> None:
        def avanzar(descargado: int, total: int) -> None:
            fraccion = descargado / total if total else 0.0
            self.colas.put(("progress", fraccion, False))

        try:
            archivo = updater.descargar(informacion, avanzar)
            self.colas.put(("downloaded", archivo, False))
        except Exception as error:  # noqa: BLE001 - se informa al usuario
            self.colas.put(("error_download", str(error), False))

    def _cerrar_progreso(self) -> None:
        if self.progreso is not None:
            self.progreso.destroy()
            self.progreso = None

    def _confirmar_instalacion(self, archivo) -> None:
        if is_frozen():
            aceptado = messagebox.askyesno(
                "Actualización descargada",
                "La nueva versión está lista. El programa se cerrará para instalarla "
                "y volverá a abrirse automáticamente.\n\n¿Continuar ahora?",
                parent=self.root,
            )
            if not aceptado:
                self._estado("Actualización descargada. Se instalará al reiniciar.")
                return
            try:
                updater.instalar(archivo)
            except Exception as error:  # noqa: BLE001 - se informa al usuario
                messagebox.showerror("No se pudo instalar", str(error), parent=self.root)
                return
            self.root.destroy()
        else:
            aceptado = messagebox.askyesno(
                "Actualización descargada",
                f"El archivo se guardó en:\n{archivo}\n\n¿Abrir la carpeta?",
                parent=self.root,
            )
            if aceptado:
                updater.mostrar_carpeta(archivo)

    def _poll(self) -> None:
        try:
            while True:
                tipo, contenido, manual = self.colas.get_nowait()
                if tipo == "check":
                    if contenido.available:
                        self._estado(f"Actualización v{contenido.version} disponible.")
                        if manual:
                            notas = contenido.notes[:400]
                            mensaje = f"Hay una versión nueva: {contenido.version}."
                            if notas:
                                mensaje += f"\n\nNovedades:\n{notas}"
                            mensaje += "\n\n¿Descargar e instalar ahora?"
                            if messagebox.askyesno(
                                "Actualización disponible", mensaje, parent=self.root
                            ):
                                self._descargar(contenido)
                    else:
                        mensaje = "Ya tienes la versión más reciente."
                        self._estado(mensaje)
                        if manual:
                            messagebox.showinfo("Actualizaciones", mensaje, parent=self.root)
                elif tipo == "error_check":
                    self._estado(f"No se pudo comprobar actualizaciones: {contenido[:90]}")
                    if manual:
                        messagebox.showerror(
                            "Actualizaciones",
                            f"No se pudo conectar con GitHub:\n{contenido}",
                            parent=self.root,
                        )
                elif tipo == "progress":
                    if self.progreso is not None:
                        self.progreso.actualizar(contenido)
                elif tipo == "downloaded":
                    self._cerrar_progreso()
                    self._confirmar_instalacion(contenido)
                elif tipo == "error_download":
                    self._cerrar_progreso()
                    self._estado("La descarga de la actualización falló.")
                    messagebox.showerror(
                        "Error de descarga", str(contenido), parent=self.root
                    )
        except queue.Empty:
            pass
        self.root.after(150, self._poll)
