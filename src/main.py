from pathlib import Path
import sys

# Asegurar ruta raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# Importar funciones comunes
from common.extract_name_file import extract_file_name
from common.extract_titles import extract_titles

INPUT_DIR = PROJECT_ROOT / "data" / "input"


def choose_pdf(input_dir: Path) -> Path | None:
    """Permite al usuario elegir un PDF de la carpeta input"""
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


def main():
    print("=== Conversor IA — Pasos 1 y 2: Nombre y Títulos (multi-línea) ===")

    # 1️⃣ Seleccionar PDF
    pdf_path = choose_pdf(INPUT_DIR)
    if not pdf_path:
        return

    # 2️⃣ Extraer nombre
    file_name = extract_file_name(pdf_path)
    print(f"\n🧾 Nombre del archivo extraído: {file_name}")

    # 3️⃣ Pedir número de página
    while True:
        page_input = input("\n👉 Ingresa el número de página que deseas extraer: ").strip()
        if page_input.isdigit() and int(page_input) > 0:
            page_number = int(page_input)
            break
        print("Número inválido. Intenta de nuevo.")

    # 4️⃣ Extraer títulos (hasta 5 líneas)
    titles = extract_titles(pdf_path, page_number, max_titles=5)

    print(f"\n📑 Títulos detectados en la página {page_number}:")
    for i, t in enumerate(titles, 1):
        print(f"  {i}. {t}")

    print("\n✅ Etapa completada: extracción de nombre y títulos (multi-línea).")


if __name__ == "__main__":
    main()
