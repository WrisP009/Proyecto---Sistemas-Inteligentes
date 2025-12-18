from pathlib import Path
import json
import zipfile
import pandas as pd
import os

from .extractor_xml import parse_xml_invoice
from .extractor_pdf import parse_pdf_invoice
from .conciliacion import conciliar_factura
from config import CONFIG


from .ia_extractor import extraer_campos_pdf_con_ia


class AgenteSupervisor:
    """
    Agente supervisor del proceso de conciliación de facturas.

    - Percibe: carpetas con ZIPs de facturas.
    - Razona: decide cómo procesar cada ZIP y cómo manejar errores.
    - Actúa: extrae ZIPs, procesa facturas, guarda resultados y genera un resumen.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        config: dict | None = None,
        carpeta_zips: Path | None = None,
    ):
        # Config por defecto
        if config is None:
            config = CONFIG
        self.config = config

        # Directorio base
        if base_dir is None:
            base_dir = config["rutas"]["base_dir"]
        self.base_dir = base_dir

        # Rutas de trabajo (vienen de CONFIG)
        self.dir_raw = config["rutas"]["data_raw"]
        self.dir_processed = config["rutas"]["data_processed"]
        self.dir_logs = config["rutas"]["data_logs"]

        # Carpeta de ZIPs: la que llega por parámetro o la de CONFIG
        if carpeta_zips is None:
            carpeta_zips = config["rutas"]["datos_adjuntos_default"]

        self.dir_zips = carpeta_zips
        self.carpeta_zips = carpeta_zips  # alias opcional

        # Contadores globales (se recalculan al final)
        self.facturas_ok = 0
        self.facturas_con_revision = 0
        self.facturas_error = 0

        self.ids_facturas_ok = []
        self.ids_facturas_con_revision = []
        self.ids_facturas_error = []

        # Detalle para saber QUÉ revisar por factura
        self.detalle_revision = {}  # {id_factura: ["campo1", "campo2", ...]}

    # ==== Percepción ====
    def percibir_zips_pendientes(self):
        """
        Detecta todos los ZIP en la carpeta configurada para self.dir_zips.
        """
        if not self.dir_zips.exists():
            print(f"[AGENTE] ⚠ La carpeta de ZIPs no existe: {self.dir_zips}")
            return []

        zips = sorted(self.dir_zips.glob("*.zip"))
        return zips

    # ==== Acciones básicas ====
    def extraer_zip(self, zip_path: Path) -> Path:
        destino = self.dir_raw / zip_path.stem
        destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(destino)
        return destino

    def emparejar_facturas(self, carpeta_raw: Path):
        pdfs = {p.stem: p for p in carpeta_raw.glob("*.pdf")}
        xmls = {p.stem: p for p in carpeta_raw.glob("*.xml")}
        parejas = []
        for base, pdf_path in pdfs.items():
            xml_path = xmls.get(base)
            if xml_path:
                parejas.append((pdf_path, xml_path))
        return parejas

    def procesar_pareja(self, pdf_path: Path, xml_path: Path) -> dict:
        """
        Procesa una pareja PDF/XML y devuelve un dict con:
          - id_factura
          - pdf_raw
          - xml_raw
          - conciliacion
          - requiere_revision_global
          - campos_a_revisar
          - error (None o string)
        """
        id_factura = pdf_path.stem

        try:
            # 1) Extraer info de PDF y XML usando tus extractores
            fac_pdf = parse_pdf_invoice(pdf_path)
            fac_xml = parse_xml_invoice(xml_path)

            # =========================================================
            # 2) IA solo si faltan campos clave en el PDF
            #    - NO pisa lo que ya tengas
            #    - Usa XML como "hint" opcional
            # =========================================================
            ia_cfg = self.config.get("ia", {})
            ia_enabled = ia_cfg.get("enabled", False)

            api_key = (
                self.config.get("openai", {}).get("api_key")
                or os.getenv("OPENAI_API_KEY", "")
            )
            model = ia_cfg.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

            CAMPOS_CLAVE = ["cufe", "numero", "nit_emisor", "total"]

            if ia_enabled and api_key:
                faltantes = [c for c in CAMPOS_CLAVE if not fac_pdf.get(c)]
                if faltantes:
                    try:
                        fac_pdf_ia = extraer_campos_pdf_con_ia(
                            pdf_path=pdf_path,
                            api_key=api_key,
                            model=model,
                            xml_hint=fac_xml,  # ayuda al modelo, sin obligarlo
                        )

                        # Rellenar SOLO vacíos
                        for k, v in fac_pdf_ia.items():
                            if k in ["nivel_confianza", "observaciones"]:
                                continue
                            if (fac_pdf.get(k) in [None, "", "N/A"]) and v not in [None, "", "N/A"]:
                                fac_pdf[k] = v

                        # Guarda metadatos IA (opcional, útil para la interfaz)
                        fac_pdf["_ia"] = {
                            "modelo": model,
                            "nivel_confianza": fac_pdf_ia.get("nivel_confianza", None),
                            "observaciones": fac_pdf_ia.get("observaciones", []),
                            "campos_faltantes_detectados": faltantes,
                        }

                    except Exception as e_ia:
                        # Si IA falla, NO dañamos el flujo
                        fac_pdf["_ia"] = {
                            "modelo": model,
                            "error": f"IA fallo: {str(e_ia)}"
                        }

            # 3) Conciliar ambas fuentes campo por campo
            conciliacion, requiere_revision_global = conciliar_factura(
                fac_pdf,
                fac_xml,
                self.config,
            )

            # Campos específicos a revisar (para que el resumen NO sea solo número)
            campos_a_revisar = [
                campo for campo, det in (conciliacion or {}).items()
                if isinstance(det, dict) and det.get("requiere_revision") is True
            ]

            return {
                "id_factura": id_factura,
                "pdf_raw": fac_pdf,
                "xml_raw": fac_xml,
                "conciliacion": conciliacion,
                "requiere_revision_global": requiere_revision_global,
                "campos_a_revisar": campos_a_revisar,
                "error": None,
            }

        except Exception as e:
            # No reventamos el flujo, marcamos la factura como error
            return {
                "id_factura": id_factura,
                "pdf_raw": None,
                "xml_raw": None,
                "conciliacion": None,
                "requiere_revision_global": True,
                "campos_a_revisar": [],
                "error": str(e),
            }

    def actuar_guardar_resultados_zip(self, carpeta_zip: Path, resultados: list):
        """
        Guarda:
          - Un JSON por factura.
          - Un CSV resumen por ZIP.
        """
        carpeta_out = self.dir_processed / carpeta_zip.name
        carpeta_out.mkdir(parents=True, exist_ok=True)

        registros_resumen = []

        for res in resultados:
            json_path = carpeta_out / f"{res['id_factura']}_conciliacion.json"
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=4, default=str)

            registros_resumen.append({
                "id_factura": res["id_factura"],
                "requiere_revision_global": res["requiere_revision_global"],
                "campos_a_revisar": ";".join(res.get("campos_a_revisar", [])),
                "error": res["error"],
            })

        df = pd.DataFrame(registros_resumen)
        df.to_csv(
            carpeta_out / "resumen_zip.csv",
            index=False,
            encoding="utf-8-sig",
        )

    # ==== Bucle principal ====
    def ciclo_principal(self):
        """
        Bucle principal del agente:
          1. Detecta ZIPs en self.dir_zips.
          2. Por cada ZIP:
             - extrae el ZIP
             - empareja PDF/XML
             - procesa cada pareja
             - guarda JSON + CSV por ZIP
          3. A partir de TODOS los resultados, calcula resumen global
             y lo guarda en data/logs/resumen_global_agente.json
        """
        zips_pendientes = self.percibir_zips_pendientes()
        print(f"[AGENTE] ZIPs pendientes: {len(zips_pendientes)}")

        todos_los_resultados = []

        for zip_path in zips_pendientes:
            print(f"\n[AGENTE] Procesando ZIP: {zip_path.name}")
            carpeta_zip = self.extraer_zip(zip_path)
            parejas = self.emparejar_facturas(carpeta_zip)
            print(f"[AGENTE] Facturas emparejadas: {len(parejas)}")

            resultados_zip = []
            for pdf_path, xml_path in parejas:
                res = self.procesar_pareja(pdf_path, xml_path)
                resultados_zip.append(res)

            # Guarda JSON + CSV por carpeta de ese ZIP
            self.actuar_guardar_resultados_zip(carpeta_zip, resultados_zip)

            # Acumula para el resumen global
            todos_los_resultados.extend(resultados_zip)

        # === Recalcular resumen global a partir de todos_los_resultados ===
        self.facturas_ok = 0
        self.facturas_con_revision = 0
        self.facturas_error = 0

        self.ids_facturas_ok = []
        self.ids_facturas_con_revision = []
        self.ids_facturas_error = []
        self.detalle_revision = {}

        for res in todos_los_resultados:
            id_factura = res.get("id_factura")

            if res.get("error"):
                self.facturas_error += 1
                if id_factura:
                    self.ids_facturas_error.append(id_factura)

            elif res.get("requiere_revision_global"):
                self.facturas_con_revision += 1
                if id_factura:
                    self.ids_facturas_con_revision.append(id_factura)
                    self.detalle_revision[id_factura] = res.get("campos_a_revisar", [])

            else:
                self.facturas_ok += 1
                if id_factura:
                    self.ids_facturas_ok.append(id_factura)

        resumen = {
            "facturas_ok": self.facturas_ok,
            "facturas_con_revision": self.facturas_con_revision,
            "facturas_error": self.facturas_error,
            "ids_facturas_ok": self.ids_facturas_ok,
            "ids_facturas_con_revision": self.ids_facturas_con_revision,
            "ids_facturas_error": self.ids_facturas_error,
            "detalle_revision": self.detalle_revision,
        }

        print("\n[AGENTE] Resumen global:", resumen)

        resumen_path = self.dir_logs / "resumen_global_agente.json"
        with resumen_path.open("w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=4)

        return resumen
