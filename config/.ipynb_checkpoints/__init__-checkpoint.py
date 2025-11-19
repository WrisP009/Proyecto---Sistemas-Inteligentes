from pathlib import Path

# Carpeta raíz del proyecto = carpeta padre de config/
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas principales del proyecto
RUTAS = {
    "base_dir": BASE_DIR,
    "data_raw": BASE_DIR / "data" / "raw",
    "data_processed": BASE_DIR / "data" / "processed",
    "data_logs": BASE_DIR / "data" / "logs",
    "datos_adjuntos_default": BASE_DIR / "data" / "raw" / "datos_adjuntos",
}

# Nos aseguramos de que existan las carpetas clave
for key in ("data_raw", "data_processed", "data_logs", "datos_adjuntos_default"):
    RUTAS[key].mkdir(parents=True, exist_ok=True)

# Configuración general del sistema inteligente
CONFIG = {
    "rutas": RUTAS,
    "prioridad_fuente": {
        "montos": "xml",          # subtotal, impuestos, total
        "nit": "xml",             # nit_emisor, cufe, numero
        "textos_libres": "pdf",   # descripciones, etc.
    },
    "comparacion": {
        "tolerancia_montos": 1.0,  # diferencia permitida para considerar montos iguales
    },
}
