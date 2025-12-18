from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# Carpeta raíz del proyecto = carpeta padre de config/
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar .env desde la raíz del proyecto
load_dotenv(BASE_DIR / ".env")

# Archivo JSON de configuración
CONFIG_FILE = Path(__file__).resolve().parent / "config_basica.json"


def _deep_update(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """Merge recursivo (extra pisa base)."""
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def _default_config() -> Dict[str, Any]:
    rutas = {
        "base_dir": BASE_DIR,
        "data_raw": BASE_DIR / "data" / "raw",
        "data_processed": BASE_DIR / "data" / "processed",
        "data_logs": BASE_DIR / "data" / "logs",
        # por defecto, busca ZIPs en /datos_adjuntos (como tú lo usas)
        "datos_adjuntos": BASE_DIR / "datos_adjuntos",
        # alias por compatibilidad con código anterior
        "datos_adjuntos_default": BASE_DIR / "datos_adjuntos",
    }

    return {
        "rutas": rutas,
        "prioridad_fuente": {
            "montos": "xml",
            "impuestos": "xml",
            "total": "xml",
            "nit": "xml",
            "textos_libres": "pdf",
        },
        "comparacion": {
            "tolerancia_montos": 1.0,
            "tolerancia_fechas_dias": 0,
        },
        # Para el módulo IA (api key por variable de entorno)
        "ia": {
            "enabled": False,
            "model": "gpt-4o-mini",
        },
        "openai": {
            "api_key": "",
        },
    }


# 1) Base defaults
CONFIG: Dict[str, Any] = _default_config()

# 2) Cargar JSON si existe
if CONFIG_FILE.exists():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        cfg_json = json.load(f)
    CONFIG = _deep_update(CONFIG, cfg_json)

# 3) Convertir rutas (str) -> Path y crear alias
rutas = CONFIG.get("rutas", {})
for k, v in list(rutas.items()):
    if isinstance(v, str) and v.strip():
        rutas[k] = Path(v)

# alias por compatibilidad
if "datos_adjuntos_default" not in rutas:
    rutas["datos_adjuntos_default"] = rutas.get("datos_adjuntos")

# base_dir si no venía
if "base_dir" not in rutas:
    # intenta inferir desde data_raw
    dr = rutas.get("data_raw")
    rutas["base_dir"] = dr.parents[2] if isinstance(dr, Path) else BASE_DIR

CONFIG["rutas"] = rutas

# 4) API KEY: si no está en JSON, tomar del entorno
if not CONFIG.get("openai", {}).get("api_key"):
    CONFIG.setdefault("openai", {})
    CONFIG["openai"]["api_key"] = os.getenv("OPENAI_API_KEY", "")

# 5) Asegurar carpetas clave
for key in ("data_raw", "data_processed", "data_logs"):
    p = rutas.get(key)
    if isinstance(p, Path):
        p.mkdir(parents=True, exist_ok=True)

# Export opcional
RUTAS = rutas
