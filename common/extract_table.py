"""
extract_table.py

Extrae la primera tabla encontrada en una página de un archivo PDF y la devuelve como un DataFrame de pandas.
"""

import pdfplumber
import pandas as pd
from typing import Optional

def extract_table_from_pdf(pdf_path: str, page_number: int) -> Optional[pd.DataFrame]:
    """
    Extrae una tabla de una página específica de un PDF.

    Args:
        pdf_path: La ruta al archivo PDF.
        page_number: El número de página (1-based) del cual extraer la tabla.

    Returns:
        Un DataFrame de pandas con los datos de la tabla, o None si no se encuentra ninguna tabla.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                print(f"⚠️  Advertencia: El número de página {page_number} está fuera del rango (1-{len(pdf.pages)}).")
                return None

            page = pdf.pages[page_number - 1]
            table = page.extract_table()

            if table:
                # La primera fila es el encabezado, el resto son los datos
                df = pd.DataFrame(table[1:], columns=table[0])
                return df
            else:
                print(f"ℹ️  No se encontraron tablas en la página {page_number}.")
                return None
    except Exception as e:
        print(f"❌ Error extrayendo la tabla: {e}")
        return None
