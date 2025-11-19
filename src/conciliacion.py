from decimal import Decimal
from src.normalizacion import normalizar_nit, normalizar_monto, normalizar_fecha

def conciliar_campo(campo: str, valor_pdf, valor_xml, config: dict) -> dict:
    """
    Aplica reglas para decidir:
      - valor_resuelto
      - fuente_elegida
      - requiere_revision
      - razon_ia (explicación)

    Este módulo es el núcleo del 'sistema inteligente' basado en reglas.
    """

    # 1. Normalización según tipo de campo
    if campo == "nit_emisor":
        v_pdf = normalizar_nit(valor_pdf)
        v_xml = normalizar_nit(valor_xml)
    elif campo in ["subtotal", "impuestos", "total"]:
        v_pdf = normalizar_monto(valor_pdf)
        v_xml = normalizar_monto(valor_xml)
    elif campo in ["fecha_emision", "fecha_vencimiento"]:
        v_pdf = normalizar_fecha(valor_pdf)
        v_xml = normalizar_fecha(valor_xml)
    else:
        v_pdf = valor_pdf.strip() if isinstance(valor_pdf, str) else valor_pdf
        v_xml = valor_xml.strip() if isinstance(valor_xml, str) else valor_xml

    #REGLA ESPECIAL: fecha_vencimiento NO genera revisión
    if campo == "fecha_vencimiento":
        # prioridad suave: XML > PDF, pero nunca pedimos revisión
        if v_xml is not None:
            fuente = "xml"
            valor_resuelto = v_xml
        elif v_pdf is not None:
            fuente = "pdf"
            valor_resuelto = v_pdf
        else:
            fuente = "indefinido"
            valor_resuelto = None

        return {
            "valor_pdf_normalizado": v_pdf,
            "valor_xml_normalizado": v_xml,
            "valor_resuelto": valor_resuelto,
            "fuente_elegida": fuente,
            "requiere_revision": False,
            "razon_ia": (
                "La fecha de vencimiento es informativa y no se utiliza como criterio "
                "para marcar revisión."
            ),
        }

    # 2. Ninguna fuente tiene valor
    if v_pdf is None and v_xml is None:
        # Para montos, asumimos que "no hay valor" no es crítico
        if campo in ["subtotal", "impuestos", "total"]:
            return {
                "valor_pdf_normalizado": v_pdf,
                "valor_xml_normalizado": v_xml,
                "valor_resuelto": None,
                "fuente_elegida": "indefinido",
                "requiere_revision": False,
                "razon_ia": (
                    f"Ambas fuentes sin valor para {campo}. "
                    "Se asume que el monto no aplica o es cero, sin requerir revisión."
                ),
            }
        # Para campos clave (cufe, nit, número, etc.) sí seguimos marcando revisión
        return {
            "valor_pdf_normalizado": v_pdf,
            "valor_xml_normalizado": v_xml,
            "valor_resuelto": None,
            "fuente_elegida": "indefinido",
            "requiere_revision": True,
            "razon_ia": "Ninguna fuente tiene valor para este campo."
        }

    # 3. Ambos coinciden
    if v_pdf == v_xml:
        return {
            "valor_pdf_normalizado": v_pdf,
            "valor_xml_normalizado": v_xml,
            "valor_resuelto": v_xml,
            "fuente_elegida": "iguales",
            "requiere_revision": False,
            "razon_ia": "Ambas fuentes coinciden tras normalizar."
        }

    prioridad_cfg = config.get("prioridad_fuente", {})
    tolerancia_montos = Decimal(str(config["comparacion"]["tolerancia_montos"]))

    # 4. Montos con tolerancia
    if campo in ["subtotal", "impuestos", "total"] and isinstance(v_pdf, Decimal) and isinstance(v_xml, Decimal):
        diff = abs(v_pdf - v_xml)
        if diff <= tolerancia_montos:
            return {
                "valor_pdf_normalizado": v_pdf,
                "valor_xml_normalizado": v_xml,
                "valor_resuelto": v_xml,
                "fuente_elegida": "xml",
                "requiere_revision": False,
                "razon_ia": f"Diferencia ({diff}) <= tolerancia. Se toma XML por política."
            }

        fuente = "xml" if prioridad_cfg.get("montos", "xml") == "xml" else "pdf"
        valor_resuelto = v_xml if fuente == "xml" else v_pdf
        return {
            "valor_pdf_normalizado": v_pdf,
            "valor_xml_normalizado": v_xml,
            "valor_resuelto": valor_resuelto,
            "fuente_elegida": fuente,
            "requiere_revision": True,
            "razon_ia": "Diferencia en montos supera tolerancia. Se aplica prioridad, pero requiere revisión humana."
        }

    # 5. Otros campos de texto o NIT
    if campo in ["nit_emisor", "numero", "cufe"]:
        fuente = prioridad_cfg.get("nit", "xml")
    else:
        fuente = prioridad_cfg.get("textos_libres", "pdf")

    valor_resuelto = v_xml if fuente == "xml" else v_pdf

    return {
        "valor_pdf_normalizado": v_pdf,
        "valor_xml_normalizado": v_xml,
        "valor_resuelto": valor_resuelto,
        "fuente_elegida": fuente,
        "requiere_revision": False,
        "razon_ia": f"Regla de prioridad: se elige {fuente.upper()} para el campo {campo}."
    }

def conciliar_factura(pdf_raw: dict, xml_raw: dict, config: dict):
    """
    Orquesta la conciliación de una factura completa, campo por campo,
    usando conciliar_campo.

    Devuelve:
      - dict_conciliacion: dict con la conciliación de cada campo
      - requiere_revision_global: bool si algún campo requiere revisión
    """

    # Campos que queremos conciliar a nivel de cabecera
    CAMPOS = [
        "cufe",
        "numero",
        "nit_emisor",
        "fecha_emision",
        "fecha_vencimiento",
        "subtotal",
        "impuestos",
        "total",
    ]

    conciliacion_por_campo = {}
    requiere_revision_global = False

    # Por seguridad, si vienen None, los tratamos como dict vacío
    pdf_raw = pdf_raw or {}
    xml_raw = xml_raw or {}

    for campo in CAMPOS:
        valor_pdf = pdf_raw.get(campo)
        valor_xml = xml_raw.get(campo)

        detalle = conciliar_campo(campo, valor_pdf, valor_xml, config)
        conciliacion_por_campo[campo] = detalle

        if detalle.get("requiere_revision"):
            requiere_revision_global = True

    return conciliacion_por_campo, requiere_revision_global

