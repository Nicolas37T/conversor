import pdfplumber
import pandas as pd


def extract_table_from_pdf(pdf_file: str, page_number: int) -> pd.DataFrame:
    """
    Extrae una tabla desde una página específica de un PDF (caso SOAT).
    Limpia espacios, completa cabeceras y corrige desplazamientos detectados.
    Devuelve un DataFrame con la tabla estructurada.
    """
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[page_number - 1]
        table = page.extract_table()

    if not table:
        raise ValueError(f"No se encontró una tabla en la página {page_number}")

    # Convertir a DataFrame
    df = pd.DataFrame(table).fillna("").astype(str)

    # Limpiar espacios
    for col in df.columns:
        df[col] = df[col].str.strip()

    # Validar estructura básica
    if df.shape[1] < 3:
        raise ValueError(f"La tabla en la página {page_number} parece incompleta (menos de 3 columnas)")

    # Rellenar primera columna vacía (nombres de departamentos o secciones)
    df.iloc[:, 0] = df.iloc[:, 0].replace("", pd.NA).ffill().fillna("")

    # Ajustar cabeceras incompletas (MOTOCICLETA, TOTAL GENERAL)
    header_row = df.iloc[0].tolist()
    for i, header in enumerate(header_row):
        if not header.strip():
            continue

        if "MOTOCICLETA" in header.upper() and i + 1 < len(df.columns):
            if df.iloc[1, i] == "" and df.iloc[1, i + 1] != "":
                df.iloc[0, i] = ""
                df.iloc[0, i + 1] = header

        elif ("TOTAL" in header.upper() and "GENERAL" in header.upper()) and i + 1 < len(df.columns):
            if df.iloc[1, i] == "" and df.iloc[1, i + 1] != "":
                df.iloc[0, i] = ""
                df.iloc[0, i + 1] = header

    # Corregir desplazamientos en filas de totales
    for idx in df.index:
        first_cell = df.iloc[idx, 0].upper().strip()

        if "TOTAL PANDO" in first_cell or "TOTAL GENERAL" in first_cell:
            # Corrección en bloque de Motocicleta
            if len(df.columns) > 5 and df.iloc[idx, 4] and not df.iloc[idx, 5]:
                df.iloc[idx, 5] = df.iloc[idx, 4]
                df.iloc[idx, 4] = ""

            # Corrección en bloque de Total General
            if len(df.columns) > 28 and df.iloc[idx, 27] and not df.iloc[idx, 28]:
                df.iloc[idx, 28] = df.iloc[idx, 27]
                df.iloc[idx, 27] = ""

    # 🔹 NUEVO PASO: eliminar columnas vacías o sin información útil
    df = df.loc[:, (df != "").any(axis=0)]  # elimina columnas completamente vacías
    df.columns = range(len(df.columns))      # reindexa columnas con números consecutivos

    return df
