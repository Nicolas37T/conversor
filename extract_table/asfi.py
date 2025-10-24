"""
Extractor específico para tablas ASFI - Disponibilidades e Inversiones Temporarias
Página 4 del PDF "carta informativa"
"""
import pdfplumber
import pandas as pd
import numpy as np
import re
from pathlib import Path


def _clean_text(text: str) -> str:
    """Limpia texto eliminando espacios extras y caracteres especiales"""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _parse_number(text) -> float:
    """Convierte texto a número, manejando formatos con puntos, comas y paréntesis."""
    if isinstance(text, (pd.Series, list, tuple)):
        if len(text) > 0:
            text = text[0]
        else:
            return np.nan

    if text is None:
        return np.nan

    text = str(text).strip()
    if text.lower() in ["nan", "none", ""]:
        return np.nan

    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]

    text = text.replace(".", "").replace(",", ".")
    text = re.sub(r"[^\d\-.]", "", text)

    try:
        return float(text)
    except ValueError:
        return np.nan


def extract_asfi_table(pdf_path: Path, page_number: int, save_temp: bool = True) -> pd.DataFrame:
    """
    Extrae la tabla de Disponibilidades e Inversiones Temporarias de ASFI
    """
    print(f"📄 Extrayendo tabla ASFI de {pdf_path.name} - Página {page_number}")

    with pdfplumber.open(pdf_path) as pdf:
        if page_number > len(pdf.pages):
            raise ValueError(f"❌ El PDF solo tiene {len(pdf.pages)} páginas")

        page = pdf.pages[page_number - 1]
        words = page.extract_words(
            x_tolerance=2,
            y_tolerance=3,
            keep_blank_chars=False
        )

    if not words:
        raise ValueError("❌ No se pudieron extraer palabras de la página")

    print(f"   ✓ Extraídas {len(words)} palabras")

    # Agrupar por línea
    lines_dict = {}
    for w in words:
        y_pos = round(w["top"], 1)
        lines_dict.setdefault(y_pos, []).append(w)

    sorted_lines = sorted(lines_dict.items(), key=lambda x: x[0])
    print(f"   ✓ Agrupadas en {len(sorted_lines)} líneas")

    # Buscar encabezado
    header_line_idx = None
    header_words = None
    for idx, (_, line_words) in enumerate(sorted_lines):
        line_words_sorted = sorted(line_words, key=lambda w: w["x0"])
        line_text = " ".join(w["text"].upper() for w in line_words_sorted)
        if "MN+UFV" in line_text or "MNUFV" in line_text:
            if "ME+MV" in line_text or "MEMV" in line_text:
                if "TOTAL" in line_text:
                    header_line_idx = idx
                    header_words = line_words_sorted
                    print(f"   ✓ Encabezado encontrado en línea {idx}")
                    break

    if header_line_idx is None:
        raise ValueError("❌ No se encontró el encabezado esperado (MN+UFV, ME+MV, TOTAL)")

    # Posiciones de columnas
    col_positions, col_names = [], []
    for w in header_words:
        t = w["text"].upper()
        if "MN" in t and "UFV" in t:
            col_positions.append(w["x0"])
            col_names.append("MNUFV")
        elif "ME" in t and "MV" in t:
            col_positions.append(w["x0"])
            col_names.append("MEMV")
        elif "TOTAL" in t and len(t) <= 10:
            col_positions.append(w["x0"])
            col_names.append("TOTAL")

    if len(col_positions) < 3:
        raise ValueError("❌ Se esperaban al menos 3 columnas numéricas")

    print(f"   ✓ Detectadas {len(col_positions)} columnas: {col_names}")

    # Límites de columnas
    left_limit = min(w["x0"] for w in words) - 10
    first_col_limit = (left_limit + col_positions[0]) / 2
    column_boundaries = []

    for i, x in enumerate(col_positions):
        if i == 0:
            column_boundaries.append((first_col_limit, x))
        else:
            mid = (col_positions[i - 1] + x) / 2
            column_boundaries.append((mid, x))
    right_limit = max(w["x1"] for w in words) + 10
    column_boundaries.append((col_positions[-1], right_limit))

    print("   ✓ Límites de columnas calculados")

    # Extraer filas
    data_rows = []
    for _, line_words in sorted_lines[header_line_idx + 1:]:
        line_words_sorted = sorted(line_words, key=lambda w: w["x0"])
        if not line_words_sorted:
            continue

        line_text = " ".join(w["text"] for w in line_words_sorted).strip()
        if not line_text or re.match(r"^(NOTA|EN MILLONES|VARIACIÓN|A PARTIR|INCLUYE)", line_text.upper()):
            continue

        row = [""] * (len(col_names) + 1)
        concept_parts = []

        for w in line_words_sorted:
            x, t = w["x0"], _clean_text(w["text"])
            if not t:
                continue
            if x < first_col_limit:
                concept_parts.append(t)
            else:
                assigned = False
                for col_idx, (left, _) in enumerate(column_boundaries):
                    if left <= x < left + 100:
                        # ✅ uso .iloc para evitar FutureWarning
                        prev = row[col_idx + 1]
                        row[col_idx + 1] = (prev + " " + t).strip() if prev else t
                        assigned = True
                        break
                if not assigned:
                    distances = [abs(x - cp) for cp in col_positions]
                    closest_idx = int(np.argmin(distances))
                    prev = row[closest_idx + 1]
                    row[closest_idx + 1] = (prev + " " + t).strip() if prev else t

        row[0] = " ".join(concept_parts).strip()
        if row[0] or any(row[1:]):
            data_rows.append(row)

    print(f"   ✓ Procesadas {len(data_rows)} filas de datos")

    df = pd.DataFrame(data_rows, columns=["CONCEPTO"] + col_names)

    for col in col_names:
        df[col] = df[col].apply(_parse_number)

    df = df.dropna(how="all", subset=col_names)
    df = df[~((df["CONCEPTO"] == "") & df[col_names].isna().all(axis=1))]
    df = df.reset_index(drop=True)

    print(f"   ✓ DataFrame final: {len(df)} filas × {len(df.columns)} columnas")

    if save_temp:
        temp_dir = pdf_path.parent.parent / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"{pdf_path.stem}_page{page_number}_asfi_temp.xlsx"
        df.to_excel(temp_file, index=False)
        print(f"   ✅ Guardado temporal en: {temp_file}")

    return df
