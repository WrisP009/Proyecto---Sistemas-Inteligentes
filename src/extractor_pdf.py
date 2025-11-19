from __future__ import annotations

from pathlib import Path
import re
import pdfplumber
from typing import Optional, Dict, Any


def _extract_text(pdf_path: Path) -> str:
    """Devuelve el texto completo del PDF (todas las páginas unidas)."""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _normalizar_monto_colombiano(valor_raw: Optional[str]) -> Optional[str]:
    """
    Convierte montos tipo '6.800.000' o '286,000.00' a '6800000.00'.
    Si no puede parsear, devuelve None.
    """
    if not valor_raw:
        return None

    s = valor_raw.strip()
    # dejar solo dígitos, puntos y comas
    s = re.sub(r"[^\d\.,]", "", s)
    if not s:
        return None

    # para simplificar: quitamos todo lo que no sea dígito
    solo_digitos = re.sub(r"\D", "", s)
    if not solo_digitos:
        return None

    n = int(solo_digitos)
    return f"{n:.2f}"


def parse_pdf_invoice(
    pdf_path: str | Path,
    xml_hint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extrae campos básicos de la factura desde el PDF.

    xml_hint = dict opcional con valores del XML
               (cufe, nit_emisor, fecha_emision, subtotal, impuestos, total)
               que usamos como guía para escoger la fecha correcta, etc.
    """
    pdf_path = Path(pdf_path)
    texto = _extract_text(pdf_path)

    resultado: Dict[str, Any] = {
        "cufe": None,
        "numero": None,
        "nit_emisor": None,
        "nombre_emisor": None,
        "fecha_emision": None,
        "fecha_vencimiento": None,
        "subtotal": None,
        "impuestos": None,
        "total": None,
        "items": [],
    }

    # ---------------- CUFE ----------------
    m_cufe = re.search(r"CUFE[:\s]+([0-9a-fA-F]{40,})", texto)
    if m_cufe:
        resultado["cufe"] = m_cufe.group(1).strip()

    # ---------------- NIT emisor ----------------
    nit_candidates = re.findall(r"\bNIT?\s+(\d+)", texto, flags=re.IGNORECASE)
    for nit in nit_candidates:
        if xml_hint and "nit_emisor" in xml_hint and xml_hint["nit_emisor"]:
            nit_xml = re.sub(r"\D", "", str(xml_hint["nit_emisor"]))
            if nit == nit_xml:
                resultado["nit_emisor"] = nit
                break
        else:
            resultado["nit_emisor"] = nit
            break

    # ---------------- Fecha de emisión ----------------
    fechas = re.findall(r"\b(\d{2})/(\d{2})/(\d{4})\b", texto)
    fecha_iso = None

    if xml_hint and xml_hint.get("fecha_emision"):
        # buscamos una fecha dd/mm/yyyy que coincida con la del XML
        try:
            y_xml, m_xml, d_xml = map(int, str(xml_hint["fecha_emision"]).split("-"))
            target = (d_xml, m_xml, y_xml)
        except Exception:
            target = None

        for d, m_, y in fechas:
            if target and (int(d), int(m_), int(y)) == target:
                fecha_iso = f"{y}-{m_}-{d}"
                break

    if not fecha_iso and fechas:
        d, m_, y = fechas[0]
        fecha_iso = f"{y}-{m_}-{d}"

    resultado["fecha_emision"] = fecha_iso

    # ---------------- Subtotal ----------------
    m_sub = re.search(r"SUBTOTAL\s+([\d\.\,]+)", texto, flags=re.IGNORECASE)
    if m_sub:
        resultado["subtotal"] = _normalizar_monto_colombiano(m_sub.group(1))

    # ---------------- Impuestos (IVA) ----------------
    iva_val = None
    for m_iva in re.finditer(r"\bIVA\b[^\d]*([\d\.\,]+)", texto):
        iva_val = m_iva.group(1)

    if iva_val:
        resultado["impuestos"] = _normalizar_monto_colombiano(iva_val)

    # ---------------- Total ----------------
    m_tot = re.search(
        r"TOTAL DE LA OPERACI[ÓO]N\s+([\d\.\,]+)",
        texto,
        flags=re.IGNORECASE,
    )
    if m_tot:
        resultado["total"] = _normalizar_monto_colombiano(m_tot.group(1))
    elif xml_hint and xml_hint.get("total"):
        resultado["total"] = str(xml_hint["total"])

    return resultado
