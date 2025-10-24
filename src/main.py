from pathlib import Path
import sys
import pandas as pd

# ------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# ------------------------------------------------------------
# IMPORTACIONES DE MÓDULOS
# ------------------------------------------------------------
from common.extract_name_file import extract_file_name
from common.process_pdf_to_long_format import process_pdf_to_long_format

# Carpeta donde estarán los PDFs
INPUT_DIR = PROJECT_ROOT / "data" / "input"


# ------------------------------------------------------------
# FUNCIÓN PARA SELECCIONAR EL PDF
# ------------------------------------------------------------
def choose_pdf(input_dir: Path) -> Path | None:
    pdfs = sorted([p for p in input_dir.glob("*.pdf")])
    if not pdfs:
        print(f"❌ No se encontraron PDFs en: {input_dir}")
        return None

    print("\n📂 PDFs disponibles:")
    for i, pdf in enumerate(pdfs, start=1):
        print(f"  {i}. {pdf.name}")

    while True:
        choice = input("Selecciona el número del PDF: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(pdfs):
            return pdfs[int(choice) - 1]
        print("Entrada inválida, intenta nuevamente.")


# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ------------------------------------------------------------
def main():
    print("=== Conversor IA — Procesamiento PDF a Excel plano ===")

    # 1️⃣ Seleccionar PDF
    pdf_path = choose_pdf(INPUT_DIR)
    if not pdf_path:
        return

    # 2️⃣ Pedir número de página
    while True:
        page_input = input("\n👉 Ingresa el número de página que deseas extraer: ").strip()
        if page_input.isdigit() and int(page_input) > 0:
            page_number = int(page_input)
            break
        print("Número inválido. Intenta de nuevo.")

    # 3️⃣ Elegir extractor
    extractor = input("➡️ Ingresa extractor (ASFI/SOAT): ").strip().upper()

    # 4️⃣ Procesar PDF a tabla plana
    df_final = process_pdf_to_long_format(str(pdf_path), page_number, extractor)

    # 5️⃣ Exportar Excel final
    output_file = PROJECT_ROOT / "data" / "output" / f"{pdf_path.stem}_page{page_number}_final.xlsx"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_excel(output_file, index=False)
    print(f"\n✅ Excel final generado: {output_file}")


# ------------------------------------------------------------
# EJECUCIÓN DIRECTA
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
