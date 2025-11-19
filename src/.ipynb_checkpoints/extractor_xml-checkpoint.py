from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Union, Dict, Any
import re


def _parse_decimal(valor: str):
    """
    Convierte un string a Decimal, devolviendo None si no se puede.
    Asume formato tipo '8092000.00' (como en los XML de DIAN).
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    # Quitar espacios, por si acaso
    texto = texto.replace(" ", "")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def parse_xml_invoice(xml_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extrae campos clave de un XML DIAN (AttachedDocument con Invoice dentro).
    Reutiliza la misma idea de tu código C#: regex sobre el contenido completo.
    Devuelve:
      - cufe
      - numero (ID de la factura o ParentDocumentID)
      - nit_emisor
      - fecha_emision (YYYY-MM-DD)
      - subtotal
      - impuestos
      - total
    """
    xml_path = Path(xml_path)
    contenido = xml_path.read_text(encoding="utf-8", errors="ignore")

    # -----------------------------
    # CUFE: primero intentamos UUID (CUFE-SHA384), luego QRCode
    # -----------------------------
    cufe = None

    # UUID dentro del Invoice (CUFE-SHA384)
    m_cufe_uuid = re.search(
        r"<cbc:UUID[^>]*schemeName=\"CUFE-SHA384\"[^>]*>([0-9a-fA-F]+)</cbc:UUID>",
        contenido,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m_cufe_uuid:
        cufe = m_cufe_uuid.group(1).strip()

    if not cufe:
        # Como en tu C#: desde sts:QRCode, documentkey=...
        m_qr = re.search(
            r"<\s*sts:QRCode\b[^>]*>(.*?)</\s*sts:QRCode\s*>",
            contenido,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m_qr:
            qr_text = m_qr.group(1).strip()
            m_doc_key = re.search(
                r"documentkey=([0-9a-fA-F]+)",
                qr_text,
                flags=re.IGNORECASE,
            )
            if m_doc_key:
                cufe = m_doc_key.group(1).strip()

    # -----------------------------
    # NUMERO de la factura
    # -----------------------------
    # Opción 1: ID del AttachedDocument (277 en tu ejemplo)
    m_num1 = re.search(
        r"<cbc:ID>(\s*\d+\s*)</cbc:ID>",
        contenido,
        flags=re.IGNORECASE,
    )
    numero = m_num1.group(1).strip() if m_num1 else None

    # Opción 2 (alternativa): ParentDocumentID (FE2259)
    # Si quisieras usar ese como "numero real" de factura:
    m_parent = re.search(
        r"<cbc:ParentDocumentID>(.*?)</cbc:ParentDocumentID>",
        contenido,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parent_document_id = m_parent.group(1).strip() if m_parent else None
    # De momento dejamos `numero` como el ID numérico (277),
    # pero guardamos parent_document_id por si lo quieres usar luego.
    # (Podríamos cambiar esto en el futuro.)

    # -----------------------------
    # NIT EMISOR: AccountingSupplierParty
    # -----------------------------
    m_nit = re.search(
        r"<cac:AccountingSupplierParty>.*?"
        r"<cbc:CompanyID[^>]*>(\d+)</cbc:CompanyID>",
        contenido,
        flags=re.IGNORECASE | re.DOTALL,
    )
    nit_emisor = m_nit.group(1).strip() if m_nit else None

    # -----------------------------
    # FECHA EMISION: IssueDate (YYYY-MM-DD)
    # -----------------------------
    m_fecha = re.search(
        r"<cbc:IssueDate>(\d{4}-\d{2}-\d{2})</cbc:IssueDate>",
        contenido,
        flags=re.IGNORECASE,
    )
    fecha_emision = m_fecha.group(1) if m_fecha else None

    # (Si quisieras forzar que venga de xades:SigningTime, podríamos
    # replicar tu regex C#, pero para el proyecto basta con IssueDate.)

    # -----------------------------
    # SUBTOTAL, IMPUESTOS, TOTAL
    # Tomados de <cac:LegalMonetaryTotal> y <cac:TaxTotal>
    # -----------------------------
    # subtotal: tomamos TaxExclusiveAmount (base antes de IVA)
    m_subtotal = re.search(
        r"<cbc:TaxExclusiveAmount\s+currencyID=\"COP\"\s*>([^<]+)</cbc:TaxExclusiveAmount>",
        contenido,
        flags=re.IGNORECASE,
    )
    subtotal = _parse_decimal(m_subtotal.group(1)) if m_subtotal else None

    # impuestos: TaxTotal/TaxAmount
    m_impuestos = re.search(
        r"<cac:TaxTotal>.*?<cbc:TaxAmount\s+currencyID=\"COP\"\s*>([^<]+)</cbc:TaxAmount>",
        contenido,
        flags=re.IGNORECASE | re.DOTALL,
    )
    impuestos = _parse_decimal(m_impuestos.group(1)) if m_impuestos else None

    # total: PayableAmount (TOTAL FACTURA sin retenciones)
    m_total = re.search(
        r"<cbc:PayableAmount\s+currencyID=\"COP\"\s*>([^<]+)</cbc:PayableAmount>",
        contenido,
        flags=re.IGNORECASE,
    )
    total = _parse_decimal(m_total.group(1)) if m_total else None

    return {
        "cufe": cufe,
        "numero": numero,
        "parent_document_id": parent_document_id,
        "nit_emisor": nit_emisor,
        "fecha_emision": fecha_emision,
        "subtotal": subtotal,
        "impuestos": impuestos,
        "total": total,
    }
