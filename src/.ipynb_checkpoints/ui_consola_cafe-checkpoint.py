"""
Interfaz sencilla por consola para el proyecto CAFE.

- Pide al usuario la carpeta donde están los ZIP.
- Instancia el AgenteSupervisor con esa carpeta.
- Ejecuta el ciclo principal y muestra un resumen en pantalla.
"""

from pathlib import Path
from config import CONFIG
from .agente_supervisor import AgenteSupervisor


def seleccionar_carpeta_zips() -> Path:
    """
    Pide al usuario la ruta de la carpeta con ZIPs.
    Si el usuario no escribe nada, usa el valor por defecto:
    <RAIZ_PROYECTO>datos_adjuntos
    """
    base_dir = Path(__file__).resolve().parents[1]

    ruta_por_defecto = base_dir / "data" / "raw" / "datos_adjuntos"
    print("=== CAPTURA AUTOMATIZADA DE FACTURAS ELECTRÓNICAS (CAFE) ===\n")
    print("Deja vacío y presiona ENTER para usar la ruta por defecto:")
    print(f"  {ruta_por_defecto}\n")

    entrada = input("Ruta de la carpeta que contiene los ZIP: ").strip()

    if not entrada:
        carpeta = ruta_por_defecto
    else:
        carpeta = Path(entrada)

    if not carpeta.exists() or not carpeta.is_dir():
        raise FileNotFoundError(f"La ruta {carpeta} no existe o no es una carpeta.")

    return carpeta


def main():
    print("=== CAPTURA AUTOMATIZADA DE FACTURAS ELECTRÓNICAS (CAFE) ===\n")

    base_dir = CONFIG["rutas"]["base_dir"]
    ruta_defecto = CONFIG["rutas"]["datos_adjuntos_default"]

    print("Deja vacío y presiona ENTER para usar la ruta por defecto:")
    print(f"  {ruta_defecto}\n")
    ruta_input = input("Ruta de la carpeta que contiene los ZIP: ").strip()

    if ruta_input:
        carpeta_zips = Path(ruta_input)
    else:
        carpeta_zips = ruta_defecto

    print(f"\n[INFO] Carpeta de ZIPs seleccionada: {carpeta_zips}\n")

    agente = AgenteSupervisor(
        base_dir=base_dir,
        config=CONFIG,
        carpeta_zips=carpeta_zips,
    )
    resumen = agente.ciclo_principal()

    print("\n=== RESUMEN GLOBAL DEL AGENTE ===")
    print(f"Facturas OK:            {resumen['facturas_ok']}")
    print(f"Facturas con revisión:  {resumen['facturas_con_revision']}")
    print(f"Facturas con error:     {resumen['facturas_error']}")
    print("\nRevisa también data/logs/resumen_global_agente.json")


if __name__ == "__main__":
    main()
