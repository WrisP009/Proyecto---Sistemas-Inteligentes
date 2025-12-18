# src/ia_extractor.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Any

from openai import OpenAI
from pydantic import BaseModel, Field
from pypdf import PdfReader


class FacturaIA(BaseModel):
    cufe: Optional[str] = None
    numero: Optional[str] = None
    nit_emisor: Optional[str] = None
    fecha_emision: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    subtotal: Optional[str] = None
    impuestos: Optional[str] = None
    total: Optional[str] = None

    nivel_confianza: int = Field(default=70, ge=0, le=100)
    observaciones: list[str] = Field(default_factory=list)


def extraer_texto_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    partes = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        partes.append(txt)
    texto = "\n".join(partes).strip()
    # Limpieza ligera
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto


def extraer_campos_pdf_con_ia(
    pdf_path: Path,
    api_key: str,
    model: str,
    xml_hint: Optional[dict[str, Any]] = None,
) -> dict:
    texto = extraer_texto_pdf(pdf_path)

    # Hint opcional (del XML) para ayudar al modelo
    hint = ""
    if xml_hint:
        hint = (
            "\n\nHINT (XML confiable):\n"
            f"- CUFE: {xml_hint.get('cufe')}\n"
            f"- Numero: {xml_hint.get('numero')}\n"
            f"- NIT: {xml_hint.get('nit_emisor')}\n"
            f"- Total: {xml_hint.get('total')}\n"
        )

    prompt = (
        "Extrae los campos de factura desde el TEXTO del PDF.\n"
        "Devuelve los valores tal cual (sin inventar). Si un campo no está, pon null.\n"
        "Además devuelve nivel_confianza (0-100) y observaciones.\n\n"
        "TEXTO PDF:\n"
        f"{texto[:20000]}"  # límite para no mandar PDFs enormes
        f"{hint}"
    )

    client = OpenAI(api_key=api_key)

    # Structured outputs con Pydantic (Responses API)
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": "Eres un extractor de datos de facturas."},
            {"role": "user", "content": prompt},
        ],
        text_format=FacturaIA,
    )

    data: FacturaIA = response.output_parsed  # :contentReference[oaicite:2]{index=2}
    return data.model_dump()
