from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .agente_supervisor import AgenteSupervisor
from config import CONFIG


class AppCAFE(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CAFE – Captura Automatizada de Facturas Electrónicas")
        self.geometry("900x550")
        self.resizable(False, False)

        # Ruta por defecto (la misma que usas en la consola)
        self.default_zip_dir: Path = CONFIG["rutas"]["datos_adjuntos_default"]

        # --- ESTADO ---
        self.var_ruta_zips = tk.StringVar(value=str(self.default_zip_dir))

        self.var_ok = tk.IntVar(value=0)
        self.var_revision = tk.IntVar(value=0)
        self.var_error = tk.IntVar(value=0)

        # --- UI ---
        self._construir_ui()

    def _construir_ui(self):
        # Frame de selección de carpeta
        frame_top = ttk.LabelFrame(self, text="1. Selección de carpeta de ZIPs")
        frame_top.pack(fill="x", padx=10, pady=10)

        lbl_ruta = ttk.Label(frame_top, text="Carpeta ZIPs:")
        lbl_ruta.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        entry_ruta = ttk.Entry(frame_top, textvariable=self.var_ruta_zips, width=80)
        entry_ruta.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        btn_examinar = ttk.Button(frame_top, text="Buscar...", command=self.seleccionar_carpeta)
        btn_examinar.grid(row=0, column=2, padx=5, pady=5)

        # Frame de acciones
        frame_mid = ttk.LabelFrame(self, text="2. Procesamiento")
        frame_mid.pack(fill="x", padx=10, pady=5)

        btn_procesar = ttk.Button(frame_mid, text="Procesar ZIPs", command=self.procesar_zips)
        btn_procesar.grid(row=0, column=0, padx=10, pady=10)

        lbl_hint = ttk.Label(
            frame_mid,
            text="El agente leerá todos los ZIP de la carpeta indicada,\n"
                 "emparejará PDF+XML, conciliará y generará JSON/CSV en data/processed."
        )
        lbl_hint.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Frame de resumen
        frame_bottom = ttk.LabelFrame(self, text="3. Resultados del agente")
        frame_bottom.pack(fill="both", expand=True, padx=10, pady=10)

        # Subframe: contadores
        frame_counts = ttk.Frame(frame_bottom)
        frame_counts.pack(fill="x", pady=(5, 10))

        ttk.Label(frame_counts, text="Facturas OK:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(frame_counts, textvariable=self.var_ok).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frame_counts, text="Facturas con revisión:").grid(row=0, column=2, sticky="w", padx=5)
        ttk.Label(frame_counts, textvariable=self.var_revision).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(frame_counts, text="Facturas con error:").grid(row=0, column=4, sticky="w", padx=5)
        ttk.Label(frame_counts, textvariable=self.var_error).grid(row=0, column=5, sticky="w", padx=5)

        # Subframe: listas de IDs
        frame_lists = ttk.Frame(frame_bottom)
        frame_lists.pack(fill="both", expand=True)

        # Listbox de OK
        frame_ok = ttk.LabelFrame(frame_lists, text="IDs facturas OK")
        frame_ok.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.list_ok = tk.Listbox(frame_ok)
        self.list_ok.pack(fill="both", expand=True, padx=5, pady=5)

        # Listbox de revisión
        frame_rev = ttk.LabelFrame(frame_lists, text="IDs facturas con revisión")
        frame_rev.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.list_revision = tk.Listbox(frame_rev)
        self.list_revision.pack(fill="both", expand=True, padx=5, pady=5)

        # Listbox de error
        frame_err = ttk.LabelFrame(frame_lists, text="IDs facturas con error")
        frame_err.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.list_error = tk.Listbox(frame_err)
        self.list_error.pack(fill="both", expand=True, padx=5, pady=5)

    # ======================= ACCIONES =======================

    def seleccionar_carpeta(self):
        """Abrir diálogo para seleccionar la carpeta con ZIPs."""
        carpeta = filedialog.askdirectory(
            title="Selecciona la carpeta que contiene los ZIP de facturas"
        )
        if carpeta:
            self.var_ruta_zips.set(carpeta)

    def procesar_zips(self):
        """Ejecuta el ciclo principal del agente y actualiza la UI."""
        ruta_str = self.var_ruta_zips.get().strip()
        if not ruta_str:
            ruta_str = str(self.default_zip_dir)
            self.var_ruta_zips.set(ruta_str)

        carpeta_zips = Path(ruta_str)

        if not carpeta_zips.exists():
            messagebox.showerror(
                "Error",
                f"La carpeta seleccionada no existe:\n{carpeta_zips}"
            )
            return

        try:
            # Instanciamos el agente usando esta carpeta de ZIPs
            agente = AgenteSupervisor(carpeta_zips=carpeta_zips)

            # Esto ejecuta todo el flujo y devuelve el resumen global
            resumen = agente.ciclo_principal()

        except Exception as e:
            messagebox.showerror(
                "Error al procesar",
                f"Ocurrió un error durante el procesamiento:\n{e}"
            )
            return

        # Actualizamos contadores
        self.var_ok.set(resumen.get("facturas_ok", 0))
        self.var_revision.set(resumen.get("facturas_con_revision", 0))
        self.var_error.set(resumen.get("facturas_error", 0))

        # Limpiamos listas
        self.list_ok.delete(0, tk.END)
        self.list_revision.delete(0, tk.END)
        self.list_error.delete(0, tk.END)

        # Rellenamos listas con los IDs
        for fid in resumen.get("ids_facturas_ok", []):
            self.list_ok.insert(tk.END, fid)

        for fid in resumen.get("ids_facturas_con_revision", []):
            self.list_revision.insert(tk.END, fid)

        for fid in resumen.get("ids_facturas_error", []):
            self.list_error.insert(tk.END, fid)

        messagebox.showinfo(
            "Proceso completado",
            "El agente terminó de procesar los ZIP.\n"
            "También puedes revisar los JSON/CSV en la carpeta data/processed\n"
            "y el resumen global en data/logs/resumen_global_agente.json."
        )


def main():
    app = AppCAFE()
    app.mainloop()


if __name__ == "__main__":
    main()
