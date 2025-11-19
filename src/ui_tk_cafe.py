import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from config import CONFIG
from .agente_supervisor import AgenteSupervisor

# Paleta de colores similar a tus mockups
COLOR_HEADER = "#204A83"
COLOR_BODY = "#FFFFFF"
COLOR_FOOTER = "#204A83"
COLOR_BOTON = "#204A83"
COLOR_BOTON_TEXTO = "#FFFFFF"
COLOR_TEXTO_HEADER = "#FFFFFF"
COLOR_TEXTO_NORMAL = "#000000"


class CafeApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CAFE - Captura Automatizada de Facturas Electrónicas")
        self.geometry("800x700")
        self.resizable(False, False)
        self.configure(bg=COLOR_BODY)

        self.selected_folder: Path | None = None
        self.ultimo_resumen: dict | None = None

        # ====== LAYOUT GENERAL ======
        self._build_header()
        self._build_footer()

        # Contenedor central donde vamos cambiando la “pantalla”
        self.content_frame = tk.Frame(self, bg=COLOR_BODY)
        self.content_frame.pack(fill="both", expand=True)

        # Pantalla inicial
        self.show_pantalla_carga()

    # ------------------------------------------------------------------
    # HEADER / FOOTER
    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=COLOR_HEADER, height=80)
        header.pack(fill="x", side="top")

        titulo = tk.Label(
            header,
            text='CAPTURA AUTOMATIZADA DE\nFACTURAS ELECTRÓNICAS "CAFE"',
            bg=COLOR_HEADER,
            fg=COLOR_TEXTO_HEADER,
            font=("Segoe UI", 16, "bold"),
            justify="left",
        )
        titulo.pack(side="left", padx=20, pady=10)

        # “Logo” simple (solo un texto redondeado)
        logo = tk.Label(
            header,
            text="CAFE",
            bg="#5C8ED8",
            fg="white",
            font=("Segoe UI", 14, "bold"),
            width=8,
            height=3,
        )
        logo.pack(side="right", padx=20, pady=10)

    def _build_footer(self):
        footer = tk.Frame(self, bg=COLOR_FOOTER, height=80)
        footer.pack(fill="x", side="bottom")

        texto = (
            'CAFE - "CAPTURA AUTOMATIZADA DE\nFACTURAS ELECTRÓNICAS"\n\n'
            "Cristian Pabon\n"
            "Iván Yamith Piñeres López\n"
            "Contacto: CAFE2@GMAIL.COM\n"
            "Teléfono: 322 959 3370\n"
            "© 2025"
        )

        lbl = tk.Label(
            footer,
            text=texto,
            bg=COLOR_FOOTER,
            fg="white",
            font=("Segoe UI", 8),
            justify="center",
        )
        lbl.pack(pady=5)

    # ------------------------------------------------------------------
    # UTILIDAD: limpiar contenido central
    # ------------------------------------------------------------------
    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    # ------------------------------------------------------------------
    # PANTALLA 1 – CARGA DE ARCHIVOS
    # ------------------------------------------------------------------
    def show_pantalla_carga(self):
        self._clear_content()

        marco = tk.Frame(self.content_frame, bg=COLOR_BODY)
        marco.pack(expand=True)

        lbl = tk.Label(
            marco,
            text="CARGA LOS ARCHIVOS",
            bg=COLOR_BOTON,
            fg=COLOR_BOTON_TEXTO,
            font=("Segoe UI", 16, "bold"),
            width=30,
            height=2,
        )
        lbl.pack(pady=40)

        btn_cargar = tk.Button(
            marco,
            text="CARGAR ARCHIVOS",
            command=self.seleccionar_carpeta,
            bg=COLOR_BOTON,
            fg=COLOR_BOTON_TEXTO,
            font=("Segoe UI", 14, "bold"),
            padx=20,
            pady=10,
            relief="flat",
        )
        btn_cargar.pack(pady=10)

    def seleccionar_carpeta(self):
        # Ruta por defecto de datos_adjuntos (la que tienes en CONFIG)
        default_dir = CONFIG["rutas"]["datos_adjuntos_default"]
        initial_dir = str(default_dir.parent) if default_dir.exists() else str(Path.home())

        carpeta = filedialog.askdirectory(
            title="Seleccione la carpeta con los ZIP de facturas",
            initialdir=initial_dir,
        )
        if not carpeta:
            return

        self.selected_folder = Path(carpeta)
        self.show_pantalla_archivo_cargado()

    # ------------------------------------------------------------------
    # PANTALLA 2 – ARCHIVOS CARGADOS, BOTÓN PROCESAR
    # ------------------------------------------------------------------
    def show_pantalla_archivo_cargado(self):
        self._clear_content()

        marco = tk.Frame(self.content_frame, bg=COLOR_BODY)
        marco.pack(expand=True)

        lbl = tk.Label(
            marco,
            text="ARCHIVOS CARGADOS\nCORRECTAMENTE",
            bg=COLOR_BOTON,
            fg=COLOR_BOTON_TEXTO,
            font=("Segoe UI", 16, "bold"),
            width=30,
            height=2,
            justify="center",
        )
        lbl.pack(pady=40)

        btn_procesar = tk.Button(
            marco,
            text="PROCESAR",
            command=self.procesar_facturas,
            bg=COLOR_BOTON,
            fg=COLOR_BOTON_TEXTO,
            font=("Segoe UI", 14, "bold"),
            padx=20,
            pady=10,
            relief="flat",
        )
        btn_procesar.pack(pady=10)

    # ------------------------------------------------------------------
    # ACCIÓN: ejecutar el AgenteSupervisor
    # ------------------------------------------------------------------
    def procesar_facturas(self):
        if self.selected_folder is None:
            messagebox.showerror("Error", "Primero debes seleccionar una carpeta.")
            return

        try:
            agente = AgenteSupervisor(carpeta_zips=self.selected_folder)
            resumen = agente.ciclo_principal()
            self.ultimo_resumen = resumen

            self.show_pantalla_resultados()

        except Exception as e:
            messagebox.showerror("Error al procesar", str(e))

    # ------------------------------------------------------------------
    # PANTALLA 3 – RESULTADOS / PROCESAMIENTO
    # ------------------------------------------------------------------
    def show_pantalla_resultados(self):
        self._clear_content()

        marco = tk.Frame(self.content_frame, bg=COLOR_BODY)
        marco.pack(expand=True, fill="both", padx=20, pady=20)

        titulo = tk.Label(
            marco,
            text="PROCESAMIENTO DE\nFACTURA ELECTRÓNICA",
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 18, "bold"),
        )
        titulo.pack(pady=10)

        # Contenedor de las dos columnas (Campos extraídos / Normalización)
        columnas = tk.Frame(marco, bg=COLOR_BODY)
        columnas.pack(pady=20)

        # Columna izquierda – Campos extraídos
        col_izq = tk.Frame(columnas, bg=COLOR_BODY, bd=1, relief="solid")
        col_izq.pack(side="left", padx=20, ipadx=10, ipady=10)

        lbl_c1_titulo = tk.Label(
            col_izq,
            text="CAMPOS EXTRAÍDOS",
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 12, "bold"),
        )
        lbl_c1_titulo.pack(pady=(5, 10))

        texto_campos = (
            "• Emisor\n"
            "• NIT\n"
            "• Número\n"
            "• Fecha\n"
            "• Subtotal\n"
            "• Impuestos\n"
            "• Total\n"
            "• Items"
        )
        lbl_c1 = tk.Label(
            col_izq,
            text=texto_campos,
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 11),
            justify="left",
        )
        lbl_c1.pack(padx=10, pady=5)

        # Columna derecha – Normalización
        col_der = tk.Frame(columnas, bg=COLOR_BODY, bd=1, relief="solid")
        col_der.pack(side="left", padx=20, ipadx=10, ipady=10)

        lbl_c2_titulo = tk.Label(
            col_der,
            text="NORMALIZACIÓN",
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 12, "bold"),
        )
        lbl_c2_titulo.pack(pady=(5, 10))

        texto_norm = (
            "• NIT solo dígitos\n"
            "• Fechas a ISO (dd-mm-yyyy)\n"
            "• Montos como Decimal,\n"
            "  sin separadores de miles\n"
            "• Mayúsculas para nombres\n"
            "• CUFE como clave de\n"
            "  emparejamiento"
        )
        lbl_c2 = tk.Label(
            col_der,
            text=texto_norm,
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 11),
            justify="left",
        )
        lbl_c2.pack(padx=10, pady=5)

        # --- Zona inferior: resumen numérico + nivel de confianza ---
        resumen = self.ultimo_resumen or {
            "facturas_ok": 0,
            "facturas_con_revision": 0,
            "facturas_error": 0,
        }
        total = (
            resumen.get("facturas_ok", 0)
            + resumen.get("facturas_con_revision", 0)
            + resumen.get("facturas_error", 0)
        )
        if total > 0:
            nivel_conf = round(100 * resumen.get("facturas_ok", 0) / total, 2)
        else:
            nivel_conf = 0.0

        info_frame = tk.Frame(marco, bg=COLOR_BODY)
        info_frame.pack(pady=20)

        lbl_conf = tk.Label(
            info_frame,
            text=f"NIVEL DE CONFIANZA: {nivel_conf:.2f} %",
            bg="#E8EDF7",
            fg="black",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=8,
        )
        lbl_conf.pack(pady=5)

        lbl_stats = tk.Label(
            info_frame,
            text=(
                f"Facturas OK: {resumen.get('facturas_ok', 0)}   |   "
                f"Con revisión: {resumen.get('facturas_con_revision', 0)}   |   "
                f"Con error: {resumen.get('facturas_error', 0)}"
            ),
            bg=COLOR_BODY,
            fg=COLOR_TEXTO_NORMAL,
            font=("Segoe UI", 11),
        )
        lbl_stats.pack(pady=5)

        # Botón “Generar JSON” (abre la carpeta de resultados)
        btn_json = tk.Button(
            marco,
            text="GENERAR JSON (VER RESULTADOS)",
            command=self.abrir_carpeta_resultados,
            bg=COLOR_BOTON,
            fg=COLOR_BOTON_TEXTO,
            font=("Segoe UI", 13, "bold"),
            padx=20,
            pady=10,
            relief="flat",
        )
        btn_json.pack(pady=10)

    # ------------------------------------------------------------------
    # Abrir carpeta con JSON/CSV procesados
    # ------------------------------------------------------------------
    def abrir_carpeta_resultados(self):
        processed_dir = CONFIG["rutas"]["data_processed"]

        if not processed_dir.exists():
            messagebox.showwarning(
                "Atención", f"No se encontró la carpeta de resultados:\n{processed_dir}"
            )
            return

        # En Windows, abre el explorador de archivos
        try:
            os.startfile(str(processed_dir))
        except Exception:
            messagebox.showinfo(
                "Ruta de resultados",
                f"Resultados en:\n{processed_dir}",
            )


def main():
    app = CafeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
