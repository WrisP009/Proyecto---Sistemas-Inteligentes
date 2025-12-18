# config/config.py
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Raíz del proyecto = carpeta padre de /config
BASE_DIR = Path(__file__).resolve().parents[1]

# Carga variables de entorno desde .env (si existe)
load_dotenv(BASE_DIR / ".env")

def _load_config_basica() -> dict:
    path = BASE_DIR / "config" / "config_basica.json"
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

_raw = _load_config_basica()

# Defaults (por si faltan llaves)
_raw.setdefault("comparacion", {})
_raw["comparacion"].setdefault("tolerancia_montos", 0)

_raw.setdefault("prioridad_fuente", {})
_raw["prioridad_fuente"].setdefault("montos", "xml")
_raw["prioridad_fuente"].setdefault("nit", "xml")
_raw["prioridad_fuente"].setdefault("textos_libres", "pdf")

_raw.setdefault("ia", {})
_raw["ia"].setdefault("enabled", True)
_raw["ia"].setdefault("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
_raw["ia"].setdefault("min_confianza", 70)

# Rutas
_raw.setdefault("rutas", {})
r = _raw["rutas"]

r["base_dir"] = BASE_DIR
r["data_raw"] = BASE_DIR / "data" / "raw"
r["data_processed"] = BASE_DIR / "data" / "processed"
r["data_logs"] = BASE_DIR / "data" / "logs"

# Carpeta default de ZIPs (si no está en JSON, usa data/raw/datos_adjuntos)
default_adj = r.get("datos_adjuntos_default", str(r["data_raw"] / "datos_adjuntos"))
r["datos_adjuntos_default"] = (BASE_DIR / default_adj) if not Path(default_adj).is_absolute() else Path(default_adj)

# Crea carpetas si no existen
for p in [r["data_raw"], r["data_processed"], r["data_logs"], r["datos_adjuntos_default"]]:
    p.mkdir(parents=True, exist_ok=True)

# OpenAI (API key)
_raw.setdefault("openai", {})
_raw["openai"]["api_key"] = os.getenv("OPENAI_API_KEY", "")

CONFIG = _raw
