"""Interfaz gráfica moderna del registro de taxímetros vendidos."""

from __future__ import annotations

import queue
import threading
from datetime import date

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database
import updater
from config import APP_TITLE, APP_VERSION, is_frozen, updates_configured

COLORES = {
    "fondo": "#F1F5F9",
    "tarjeta": "#FFFFFF",
    "borde": "#E2E8F0",
    "nav": "#0F172A",
    "nav_hover": "#1E293B",
    "nav_activo": "#2563EB",
    "texto": "#0F172A",
    "texto_suave": "#475569",
    "muted": "#94A3B8",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "ok": "#16A34A",
    "error": "#DC2626",
    "warn": "#F59E0B",
}

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
    ("id", "ID", 55),
    ("fecha", "Fecha", 105),
    ("cliente", "Cliente", 195),
    ("numero_serie", "N.º de serie", 150),
    ("tipo_carro", "Tipo de carro", 120),
    ("placas", "Placas", 100),
    ("telefono", "Teléfono", 120),
)


def configurar_estilos() -> None:
    estilo = ttk.Style()
    estilo.theme_use("clam")

    estilo.configure(
        "Treeview",
        background=COLORES["tarjeta"],
        fieldbackground=COLORES["tarjeta"],
        foreground=COLORES["texto_suave"],
        rowheight=32,
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    estilo.configure(
        "Treeview.Heading",
        background="#F8FAFC",
        foreground=COLORES["texto_suave"],
        font=("Segoe UI", 9, "bold"),
        borderwidth=0,
        relief="flat",
        padding=(8, 8),
    )
    estilo.map("Treeview.Heading", background=[("active", "#E2E8F0")])
    estilo.map(
        "Treeview",
        background=[("selected", COLORES["accent"])],
        foreground=[("selected", "#FFFFFF")],
    )

    estilo.configure(
        "Modern.TEntry",
        fieldbackground="#FFFFFF",
        foreground=COLORES["texto"],
        insertcolor=COLORES["accent"],
        bordercolor=COLORES["borde"],
        lightcolor=COLORES["borde"],
        darkcolor=COLORES["borde"],
        borderwidth=1,
        padding=7,
        font=("Segoe UI", 10),
    )
    estilo.map(
        "Modern.TEntry",
        bordercolor=[("focus", COLORES["accent"])],
        lightcolor=[("focus", COLORES["accent"])],
        darkcolor=[("focus", COLORES["accent"])],
    )

    estilo.configure(
        "Modern.TCombobox",
        fieldbackground="#FFFFFF",
        background="#FFFFFF",
        foreground=COLORES["texto"],
        arrowcolor=COLORES["texto_suave"],
        bordercolor=COLORES["borde"],
        lightcolor=COLORES["borde"],
        darkcolor=COLORES["borde"],
        borderwidth=1,
        padding=6,
        font=("Segoe UI", 10),
    )
    estilo.map(
        "Modern.TCombobox",
        bordercolor=[("focus", COLORES["accent"])],
        lightcolor=[("focus", COLORES["accent"])],
        darkcolor=[("focus", COLORES["accent"])],
    )

    estilo.configure(
        "Accent.TButton",
        background=COLORES["accent"],
        foreground="#FFFFFF",
        borderwidth=0,
        focusthickness=0,
        focuscolor=COLORES["accent"],
        padding=(18, 9),
        font=("Segoe UI", 10, "bold"),
    )
    estilo.map(
        "Accent.TButton",
        background=[("active", COLORES["accent_hover"]), ("disabled", "#93C5FD")],
    )

    estilo.configure(
        "Outline.TButton",
        background="#FFFFFF",
        foreground=COLORES["texto_suave"],
        bordercolor=COLORES["borde"],
        borderwidth=1,
        focuscolor="#FFFFFF",
        padding=(14, 9),
        font=("Segoe UI", 10),
    )
    estilo.map("Outline.TButton", background=[("active", "#F8FAFC")])

    estilo.configure(
        "Soft.TButton",
        background="#EFF6FF",
        foreground=COLORES["accent"],
        borderwidth=0,
        focuscolor="#EFF6FF",
        padding=(12, 7),
        font=("Segoe UI", 10, "bold"),
    )
    estilo.map("Soft.TButton", background=[("active", "#DBEAFE")])

    estilo.configure(
        "Accent.Horizontal.TProgressbar",
        background=COLORES["accent"],
        troughcolor=COLORES["borde"],
        borderwidth=0,
        thickness=8,
    )


class ProgressDialog(tk.Toplevel):
    """Ventana de progreso de la descarga de actualizaciones."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Actualizando")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(bg=COLORES["tarjeta"])
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        cabecera = tk.Frame(self, bg=COLORES["nav"], height=52)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)
        tk.Label(
            cabecera,
            text="Descargando actualización",
            bg=COLORES["nav"],
            fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=18)

        cuerpo = tk.Frame(self, bg=COLORES["tarjeta"], padding=(20, 18))
        cuerpo.pack(fill="both", expand=True)
        tk.Label(
            cuerpo,
            text="Obteniendo la nueva versión desde GitHub...",
            bg=COLORES["tarjeta"],
            fg=COLORES["texto_suave"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        self.barra = ttk.Progressbar(
            cuerpo,
            orient="horizontal",
            mode="determinate",
            length=360,
            maximum=100,
            style="Accent.Horizontal.TProgressbar",
        )
        self.barra.pack(fill="x", pady=(14, 8))
        self.etiqueta = tk.Label(
            cuerpo,
            text="0 %",
            bg=COLORES["tarjeta"],
            fg=COLORES["muted"],
            font=("Segoe UI", 9),
        )
        self.etiqueta.pack(anchor="e")

        self.grab_set()
        self.update_idletasks()

    def actualizar(self, fraccion: float) -> None:
        porcentaje = max(0.0, min(1.0, fraccion)) * 100
        self.barra["value"] = porcentaje
        self.etiqueta.config(text=f"{porcentaje:.0f} %")


class NavButton(tk.Button):
    """Botón del menú lateral con efecto hover y estado activo."""

    def __init__(self, padre: tk.Widget, texto: str, comando, activo: bool = False):
        super().__init__(
            padre,
            text=texto,
            command=comando,
            bd=0,
            relief="flat",
            anchor="w",
            padx=18,
            pady=10,
            font=("Segoe UI", 10, "bold" if activo else "normal"),
            fg="#FFFFFF" if activo else "#CBD5E1",
            activeforeground="#FFFFFF",
            cursor="hand2",
        )
        self.activo = activo
        self._aplicar_color()
        self.bind("<Enter>", lambda _e: self.configure(bg=COLORES["nav_activo"]))
        self.bind("<Leave>", lambda _e: self._aplicar_color())

    def _aplicar_color(self) -> None:
        self.configure(bg=COLORES["nav_activo"] if self.activo else COLORES["nav"])

    def seleccionar(self) -> None:
        for hermano in self.master.winfo_children():
            if isinstance(hermano, NavButton):
                hermano.activo = False
                hermano.configure(
                    fg="#CBD5E1", font=("Segoe UI", 10), bg=COLORES["nav"]
                )
        self.activo = True
        self.configure(
            fg="#FFFFFF", font=("Segoe UI", 10, "bold"), bg=COLORES["nav_activo"]
        )


class RegistroApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1180x860")
        self.root.minsize(1060, 740)
        self.root.configure(bg=COLORES["fondo"])

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

        configurar_estilos()
        self._crear_menu()
        self._construir_interfaz()
        self.refrescar()
        self._poll()
        self.root.after(1200, lambda: self.verificar_actualizaciones(manual=False))

    # ------------------------------------------------------------ Construcción

    def _crear_menu(self) -> None:
        barra = tk.Menu(self.root)
        archivo = tk.Menu(barra, tearoff=0)
        archivo.add_command(label="Exportar CSV", command=self.exportar_csv)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.root.destroy)
        ayuda = tk.Menu(barra, tearoff=0)
        ayuda.add_command(
            label="Buscar actualizaciones",
            command=lambda: self.verificar_actualizaciones(manual=True),
        )
        ayuda.add_command(label="Acerca de", command=self.acerca_de)
        barra.add_cascade(label="Archivo", menu=archivo)
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.root.config(menu=barra)

    def _construir_interfaz(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._construir_cabecera()

        cuerpo = tk.Frame(self.root, bg=COLORES["fondo"])
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        self._construir_lateral(cuerpo)
        self._construir_principal(cuerpo)

    def _construir_cabecera(self) -> None:
        cabecera = tk.Frame(self.root, bg=COLORES["nav"], height=68)
        cabecera.grid(row=0, column=0, sticky="ew")
        cabecera.grid_propagate(False)

        franja = tk.Frame(cabecera, bg=COLORES["accent"], width=5)
        franja.pack(side="left", fill="y")

        textos = tk.Frame(cabecera, bg=COLORES["nav"])
        textos.pack(side="left", padx=(18, 0))
        tk.Label(
            textos,
            text="Registro de Taxímetros",
            bg=COLORES["nav"],
            fg="#FFFFFF",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(12, 0))
        tk.Label(
            textos,
            text="Panel de control de ventas",
            bg=COLORES["nav"],
            fg=COLORES["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self.estado_update = tk.Label(
            cabecera,
            text="Actualizaciones: sin comprobar",
            bg=COLORES["nav"],
            fg=COLORES["muted"],
            font=("Segoe UI", 9),
        )
        self.estado_update.pack(side="right", padx=(0, 18))

        chip = tk.Frame(cabecera, bg="#1E293B", padx=10, pady=4)
        chip.pack(side="right", padx=(0, 12))
        tk.Label(
            chip,
            text=f"v{APP_VERSION}",
            bg="#1E293B",
            fg="#CBD5E1",
            font=("Segoe UI", 9, "bold"),
        ).pack()

    def _construir_lateral(self, padre: tk.Widget) -> None:
        lateral = tk.Frame(padre, bg=COLORES["nav"], width=218)
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.grid_propagate(False)

        tk.Label(
            lateral,
            text="MENÚ PRINCIPAL",
            bg=COLORES["nav"],
            fg="#64748B",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(24, 10))

        self.nav_panel = NavButton(lateral, "▦   Panel", lambda: self._nav("panel"), True)
        self.nav_panel.pack(fill="x")
        self.nav_nuevo = NavButton(
            lateral, "＋   Nueva venta", lambda: self._nav("nuevo")
        )
        self.nav_nuevo.pack(fill="x")
        self.nav_buscar = NavButton(lateral, "⌕   Buscar", lambda: self._nav("buscar"))
        self.nav_buscar.pack(fill="x")
        self.nav_exportar = NavButton(
            lateral, "⇩   Exportar CSV", lambda: self._nav("exportar")
        )
        self.nav_exportar.pack(fill="x")

        tk.Frame(lateral, bg="#1E293B", height=1).pack(fill="x", padx=18, pady=18)
        tk.Label(
            lateral,
            text="SISTEMA",
            bg=COLORES["nav"],
            fg="#64748B",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        NavButton(
            lateral,
            "↻   Actualizaciones",
            lambda: self.verificar_actualizaciones(manual=True),
        ).pack(fill="x")
        NavButton(lateral, "ⓘ   Acerca de", self.acerca_de).pack(fill="x")
        NavButton(lateral, "⎋   Salir", self.root.destroy).pack(fill="x")

        pie = tk.Frame(lateral, bg="#0B1220")
        pie.pack(side="bottom", fill="x", padx=12, pady=14)
        tk.Label(
            pie,
            text="Datos guardados en este equipo",
            bg="#0B1220",
            fg="#64748B",
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))
        texto = str(database.DB_PATH)
        if len(texto) > 32:
            texto = "…" + texto[-31:]
        tk.Label(
            pie,
            text=texto,
            bg="#0B1220",
            fg="#475569",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=10, pady=(0, 10))

    def _construir_principal(self, padre: tk.Widget) -> None:
        principal = tk.Frame(padre, bg=COLORES["fondo"], padx=20, pady=12)
        principal.grid(row=0, column=1, sticky="nsew")
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(3, weight=1)

        # Tarjetas de indicadores
        kpis = tk.Frame(principal, bg=COLORES["fondo"])
        kpis.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.kpi_total = self._tarjeta(kpis, "VENTAS REGISTRADAS", "0", COLORES["accent"])
        self.kpi_mes = self._tarjeta(kpis, "ESTE MES", "0", COLORES["ok"])
        self.kpi_ultima = self._tarjeta(
            kpis, "ÚLTIMA VENTA", "—", COLORES["warn"], con_detalle=True
        )

        # Formulario
        formulario = self._tarjeta_contenedor(principal)
        formulario.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        cabecera = tk.Frame(formulario, bg=COLORES["tarjeta"])
        cabecera.grid(row=0, column=0, columnspan=4, sticky="ew", padx=18, pady=(8, 3))
        tk.Label(
            cabecera,
            text="Nueva venta",
            bg=COLORES["tarjeta"],
            fg=COLORES["texto"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")
        self.etiqueta_edicion = tk.Label(
            cabecera,
            text="",
            bg=COLORES["tarjeta"],
            fg=COLORES["accent"],
            font=("Segoe UI", 9, "bold"),
        )
        self.etiqueta_edicion.pack(side="left", padx=12)

        for columna in (1, 3):
            formulario.columnconfigure(columna, weight=1)
        self._campo(formulario, 1, 0, "cliente", "Nombre del cliente")
        self._campo(formulario, 1, 2, "numero_serie", "N.º de serie del taxímetro")
        self._campo(formulario, 2, 0, "tipo_carro", "Tipo de carro", combo=True)
        self._campo(formulario, 2, 2, "placas", "Placas")
        self._campo(formulario, 3, 0, "telefono", "Teléfono")
        self._campo(formulario, 3, 2, "fecha", "Fecha de venta (AAAA-MM-DD)")

        botones = tk.Frame(formulario, bg=COLORES["tarjeta"])
        botones.grid(row=4, column=0, columnspan=4, sticky="e", padx=18, pady=(6, 10))
        ttk.Button(
            botones, text="Limpiar", style="Outline.TButton", command=self.limpiar
        ).pack(side="left", padx=(0, 8))
        self.boton_guardar = ttk.Button(
            botones, text="Guardar registro", style="Accent.TButton", command=self.guardar
        )
        self.boton_guardar.pack(side="left")

        # Búsqueda
        busqueda = self._tarjeta_contenedor(principal)
        busqueda.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            busqueda,
            text="Buscar registro",
            bg=COLORES["tarjeta"],
            fg=COLORES["texto"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(10, 4))
        self.entrada_busqueda = ttk.Entry(
            busqueda, textvariable=self.vars["busqueda"], style="Modern.TEntry", width=42
        )
        self.entrada_busqueda.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))
        self.entrada_busqueda.bind("<Return>", lambda _e: self.refrescar())
        acciones = tk.Frame(busqueda, bg=COLORES["tarjeta"])
        acciones.grid(row=1, column=1, sticky="e", padx=(0, 18), pady=(0, 10))
        busqueda.columnconfigure(1, weight=1)
        ttk.Button(
            acciones, text="Buscar", style="Outline.TButton", command=self.refrescar
        ).pack(side="left", padx=4)
        ttk.Button(
            acciones,
            text="Mostrar todos",
            style="Outline.TButton",
            command=self.mostrar_todos,
        ).pack(side="left", padx=4)
        ttk.Button(
            acciones,
            text="Exportar CSV",
            style="Soft.TButton",
            command=self.exportar_csv,
        ).pack(side="left", padx=4)

        # Historial
        historial = self._tarjeta_contenedor(principal)
        historial.grid(row=3, column=0, sticky="nsew")
        historial.columnconfigure(0, weight=1)
        historial.rowconfigure(1, weight=1)
        cabecera_hist = tk.Frame(historial, bg=COLORES["tarjeta"])
        cabecera_hist.grid(row=0, column=0, sticky="ew", padx=18, pady=(10, 6))
        tk.Label(
            cabecera_hist,
            text="Historial de ventas",
            bg=COLORES["tarjeta"],
            fg=COLORES["texto"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")
        self.etiqueta_tabla_count = tk.Label(
            cabecera_hist,
            text="0 registros",
            bg="#EFF6FF",
            fg=COLORES["accent"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=3,
        )
        self.etiqueta_tabla_count.pack(side="left", padx=12)
        self.boton_editar = ttk.Button(
            cabecera_hist,
            text="Editar selección",
            style="Outline.TButton",
            command=self.editar_seleccion,
            state="disabled",
        )
        self.boton_editar.pack(side="right", padx=4)
        self.boton_eliminar = ttk.Button(
            cabecera_hist,
            text="Eliminar",
            style="Outline.TButton",
            command=self.eliminar_seleccion,
            state="disabled",
        )
        self.boton_eliminar.pack(side="right", padx=4)

        marco_tabla = tk.Frame(historial, bg=COLORES["tarjeta"])
        marco_tabla.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            marco_tabla,
            columns=[c[0] for c in COLUMNAS],
            show="headings",
            selectmode="browse",
            height=9,
        )
        for clave, titulo, ancho in COLUMNAS:
            self.tree.heading(clave, text=titulo)
            self.tree.column(clave, width=ancho, anchor="w", stretch=(clave == "cliente"))
        self.tree.tag_configure("impar", background="#F8FAFC")
        self.tree.bind("<<TreeviewSelect>>", self._al_seleccionar)
        self.tree.bind("<Double-1>", lambda _e: self.editar_seleccion())

        vertical = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(marco_tabla, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        # Estado
        barra = tk.Frame(principal, bg=COLORES["fondo"])
        barra.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.status_dot = tk.Label(
            barra, text="●", bg=COLORES["fondo"], fg=COLORES["accent"], font=("Segoe UI", 11)
        )
        self.status_dot.pack(side="left")
        self.etiqueta_estado = tk.Label(
            barra,
            text="Listo.",
            bg=COLORES["fondo"],
            fg=COLORES["texto_suave"],
            font=("Segoe UI", 9),
        )
        self.etiqueta_estado.pack(side="left", padx=6)
        self.etiqueta_total = tk.Label(
            barra,
            text="0 registros",
            bg=COLORES["fondo"],
            fg=COLORES["muted"],
            font=("Segoe UI", 9),
        )
        self.etiqueta_total.pack(side="right")

    def _tarjeta(
        self,
        padre: tk.Widget,
        titulo: str,
        valor: str,
        color: str,
        con_detalle: bool = False,
    ) -> tk.Label:
        tarjeta = tk.Frame(
            padre,
            bg=COLORES["tarjeta"],
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
        )
        tarjeta.pack(side="left", fill="both", expand=True, padx=(0, 12))
        franja = tk.Frame(tarjeta, bg=color, width=4)
        franja.pack(side="left", fill="y")
        contenido = tk.Frame(tarjeta, bg=COLORES["tarjeta"])
        contenido.pack(side="left", fill="both", expand=True, padx=14, pady=6)
        etiqueta_valor = tk.Label(
            contenido,
            text=valor,
            bg=COLORES["tarjeta"],
            fg=COLORES["texto"],
            font=("Segoe UI", 17, "bold"),
        )
        etiqueta_valor.pack(anchor="w")
        tk.Label(
            contenido,
            text=titulo,
            bg=COLORES["tarjeta"],
            fg=COLORES["muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        if con_detalle:
            self.kpi_ultima_detalle = tk.Label(
                contenido,
                text="",
                bg=COLORES["tarjeta"],
                fg=COLORES["muted"],
                font=("Segoe UI", 8),
            )
            self.kpi_ultima_detalle.pack(anchor="w", pady=(2, 0))
        return etiqueta_valor

    def _tarjeta_contenedor(self, padre: tk.Widget) -> tk.Frame:
        return tk.Frame(
            padre,
            bg=COLORES["tarjeta"],
            highlightthickness=1,
            highlightbackground=COLORES["borde"],
        )

    def _campo(
        self,
        padre: tk.Widget,
        fila: int,
        columna: int,
        clave: str,
        texto: str,
        combo: bool = False,
    ) -> None:
        tk.Label(
            padre,
            text=texto,
            bg=COLORES["tarjeta"],
            fg=COLORES["texto_suave"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=fila, column=columna, sticky="w", padx=(18, 6), pady=(2, 1))
        if combo:
            widget = ttk.Combobox(
                padre,
                textvariable=self.vars[clave],
                values=TIPOS_CARRO,
                style="Modern.TCombobox",
                width=24,
            )
        else:
            widget = ttk.Entry(
                padre, textvariable=self.vars[clave], style="Modern.TEntry", width=28
            )
        widget.grid(
            row=fila,
            column=columna + 1,
            sticky="ew",
            padx=(0, 22),
            pady=(0, 2),
            ipady=1,
        )
        if clave == "cliente":
            self.entrada_cliente = widget

    def _nav(self, destino: str) -> None:
        if destino == "panel":
            self.nav_panel.seleccionar()
            self.refrescar()
            self._estado("Panel actualizado.", "ok")
        elif destino == "nuevo":
            self.nav_nuevo.seleccionar()
            self.entrada_cliente.focus_set()
            self._estado("Completa los datos de la nueva venta.")
        elif destino == "buscar":
            self.nav_buscar.seleccionar()
            self.entrada_busqueda.focus_set()
            self._estado("Escribe un nombre, serie, placa o teléfono.")
        elif destino == "exportar":
            self.nav_exportar.seleccionar()
            self.exportar_csv()

    # ------------------------------------------------------------ Operaciones

    def _estado(self, mensaje: str, tono: str = "info") -> None:
        self.etiqueta_estado.config(text=mensaje)
        colores = {
            "info": COLORES["accent"],
            "ok": COLORES["ok"],
            "error": COLORES["error"],
            "warn": COLORES["warn"],
        }
        self.status_dot.config(fg=colores.get(tono, COLORES["accent"]))

    def _estado_actualizacion(self, mensaje: str, tono: str = "info") -> None:
        colores = {
            "info": COLORES["muted"],
            "ok": "#4ADE80",
            "error": "#F87171",
            "warn": "#FBBF24",
        }
        self.estado_update.config(
            text=f"Actualizaciones: {mensaje}", fg=colores.get(tono, COLORES["muted"])
        )

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
        self.etiqueta_total.config(text=f"{total} registro(s) en total")
        self.etiqueta_tabla_count.config(
            text=f"{len(ventas)} de {total}" if terminos else f"{total} registros"
        )

        estadisticas = database.estadisticas()
        self.kpi_total.config(text=str(estadisticas["total"]))
        self.kpi_mes.config(text=str(estadisticas["del_mes"]))
        ultima = estadisticas["ultima"]
        self.kpi_ultima.config(text=ultima["fecha"] if ultima else "—")
        detalle = ""
        if ultima:
            detalle = f"{ultima['cliente']} · {ultima['numero_serie']}"
            if len(detalle) > 34:
                detalle = detalle[:33] + "…"
        self.kpi_ultima_detalle.config(text=detalle or "Sin registros aún")

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
        self._estado(mensaje, "ok")

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
        self._estado("Registro cargado. Modifícalo y guarda los cambios.")

    def eliminar_seleccion(self) -> None:
        seleccion = self.tree.selection()
        if not seleccion:
            return
        venta_id = int(seleccion[0])
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar el registro #{venta_id}? Esta acción no se puede deshacer.",
            parent=self.root,
        ):
            return
        database.eliminar(venta_id)
        if self.editing_id == venta_id:
            self.limpiar()
        self.refrescar()
        self._estado(f"Registro #{venta_id} eliminado.", "ok")

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
        self._estado(f"Se exportaron {len(ventas)} registro(s) a CSV.", "ok")

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
                    "Copia actualizaciones.example.json como actualizaciones.json "
                    "junto al programa y completa tu usuario y repositorio de GitHub.",
                    parent=self.root,
                )
            return
        self._estado_actualizacion("comprobando...", "info")
        hilo = threading.Thread(target=self._verificar_worker, args=(manual,), daemon=True)
        hilo.start()

    def _verificar_worker(self, manual: bool) -> None:
        try:
            informacion = updater.check()
            self.colas.put(("check", informacion, manual))
        except Exception as error:  # noqa: BLE001
            self.colas.put(("error_check", str(error), manual))

    def _descargar(self, informacion: updater.UpdateInfo) -> None:
        self.progreso = ProgressDialog(self.root)
        hilo = threading.Thread(
            target=self._descargar_worker, args=(informacion,), daemon=True
        )
        hilo.start()

    def _descargar_worker(self, informacion: updater.UpdateInfo) -> None:
        def avanzar(descargado: int, total: int) -> None:
            self.colas.put(("progress", descargado / total if total else 0.0, False))

        try:
            archivo = updater.descargar(informacion, avanzar)
            self.colas.put(("downloaded", archivo, False))
        except Exception as error:  # noqa: BLE001
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
                self._estado("Actualización descargada. Se instalará al reiniciar.", "warn")
                return
            try:
                updater.instalar(archivo)
            except Exception as error:  # noqa: BLE001
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
                        self._estado(f"Actualización v{contenido.version} disponible.", "warn")
                        self._estado_actualizacion(
                            f"versión {contenido.version} disponible", "warn"
                        )
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
                        self._estado_actualizacion("al día", "ok")
                        if manual:
                            self._estado(mensaje, "ok")
                            messagebox.showinfo("Actualizaciones", mensaje, parent=self.root)
                elif tipo == "error_check":
                    self._estado_actualizacion("sin conexión", "error")
                    self._estado(f"No se pudo comprobar: {contenido[:70]}", "error")
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
                    self._estado_actualizacion("descarga completada", "ok")
                    self._confirmar_instalacion(contenido)
                elif tipo == "error_download":
                    self._cerrar_progreso()
                    self._estado("La descarga de la actualización falló.", "error")
                    messagebox.showerror(
                        "Error de descarga", str(contenido), parent=self.root
                    )
        except queue.Empty:
            pass
        self.root.after(150, self._poll)
