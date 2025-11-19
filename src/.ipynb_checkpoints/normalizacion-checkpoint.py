import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Optional


def normalizar_nit(nit: Optional[str]) -> Optional[str]:
    """
    Elimina puntos, guiones y deja solo dígitos en el NIT.
    """
    if not nit:
        return None
    solo_digitos = re.sub(r"\D", "", nit)
    return solo_digitos or None


def normalizar_monto(monto: Any) -> Optional[Decimal]:
    """
    Normaliza un monto y lo devuelve como Decimal.

    Soporta:
      - str: con formatos simples tipo '8092000.00', '8092000', '8.092.000'
      - Decimal: se devuelve tal cual
      - int / float: se convierte a Decimal

    Regla principal:
      - Si el string tiene como máximo UN separador ('.' o ',') y ese separador
        va seguido de 1 o 2 dígitos -> se interpreta como DECIMAL (ej: 8092000.00).
      - En otro caso, se asume que los separadores son de miles y se eliminan.
    """
    # Caso 1: None o vacío
    if monto is None:
        return None

    # Caso 2: ya es Decimal
    if isinstance(monto, Decimal):
        return monto

    # Caso 3: int o float
    if isinstance(monto, (int, float)):
        try:
            return Decimal(str(monto))
        except InvalidOperation:
            return None

    # Caso 4: string
    if isinstance(monto, str):
        texto = monto.strip().replace(" ", "")
        if not texto:
            return None

        # Patrón: dígitos + opcionalmente (punto o coma + 1-2 dígitos)
        # Ejemplos que matchean:
        #   "8092000"
        #   "8092000.0"
        #   "8092000.00"
        #   "8092000,00"
        patron_decimal_simple = r"^\d+([.,]\d{1,2})?$"

        if re.match(patron_decimal_simple, texto):
            # Interpretamos '.' o ',' como separador decimal
            texto_decimal = texto.replace(",", ".")
            try:
                return Decimal(texto_decimal)
            except InvalidOperation:
                return None

        # Si llegamos aquí, asumimos que '.' y ',' son separadores de miles
        # Ej: "8.092.000" -> "8092000"
        solo_digitos = re.sub(r"[.,]", "", texto)
        if not solo_digitos:
            return None
        try:
            return Decimal(solo_digitos)
        except InvalidOperation:
            return None

    # Cualquier otro tipo raro -> None
    return None


def normalizar_fecha(fecha: Optional[str]) -> Optional[str]:
    """
    Intenta convertir diferentes formatos de fecha a 'YYYY-MM-DD'.
    Soporta por defecto:
      - 2024-11-17
      - 17/11/2024
      - 17-11-2024
    """
    if not fecha:
        return None
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(fecha.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
