import pdfplumber
import pandas as pd
import re
import numpy as np
from pathlib import Path
from statistics import median


def _clean_text(t: str) -> str:
    if t is None:
        return ""
    t = str(t)
    t = re.sub(r"[^\S\r\n]+", " ", t)  # normaliza espacios
    t = re.sub(r"[^\d\-\.,()A-Za-zÁÉÍÓÚÜÑáéíóúüñ/% ]", "", t)
    return t.strip()


def _num_from_str(s: str):
    if s is None:
        return np.nan
    s = str(s).strip()
    if not s:
        return np.nan
    # convertir (x) -> -x, eliminar puntos de miles, cambiar coma decimal a punto si existe
    s = s.replace(".", "").replace(",", ".")
    s = s.replace("(", "-").replace(")", "")
    # si queda solo - o no número, devolver NaN
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        try:
            return float(s)
        except:
            return np.nan
    return np.nan


def extract_asfi_table(pdf_path: Path, page_number: int, save_excel: bool = True) -> pd.DataFrame:
    """
    Extrae la tabla ASFI de la página indicada y la estructura en columnas tal como en el PDF.
    Devuelve DataFrame con columnas: CONCEPTO + (los encabezados numéricos detectados).
    """
    print(f"📖 Extrayendo tabla (estructura) de {pdf_path.name} — página {page_number} ...")

    with pdfplumber.open(pdf_path) as pdf:
        if page_number > len(pdf.pages):
            raise ValueError(f"El PDF solo tiene {len(pdf.pages)} páginas.")
        page = pdf.pages[page_number - 1]
        words = page.extract_words(x_tolerance=1, y_tolerance=3, keep_blank_chars=False)

    if not words:
        raise ValueError("No se extrajeron palabras de la página.")

    # Agrupar por 'top' (líneas)
    lines_by_y = {}
    for w in words:
        y = round(w["top"], 1)
        lines_by_y.setdefault(y, []).append(w)
    sorted_lines = sorted(lines_by_y.items(), key=lambda kv: kv[0])

    # Convertir cada línea a lista de (x0, text)
    lines = []
    for _, ws in sorted_lines:
        ws_sorted = sorted(ws, key=lambda w: w["x0"])
        lines.append([(w["x0"], _clean_text(w["text"])) for w in ws_sorted])

    # Buscar la línea de cabecera que contenga MNUFV y MEMV y TOTAL (puede repetirse)
    header_idx = None
    for i, line in enumerate(lines):
        joined = " ".join([t for _, t in line]).upper()
        if "MNUFV" in joined and "MEMV" in joined and "TOTAL" in joined:
            header_idx = i
            break
    if header_idx is None:
        # intento alternativo: buscar fila con "MN" "ME" "TOTAL" o "M N"
        for i, line in enumerate(lines):
            joined = " ".join([t for _, t in line]).upper()
            if ("MN" in joined or "MN+UFV" in joined or "MN+UFV" in joined) and "TOTAL" in joined:
                header_idx = i
                break

    if header_idx is None:
        raise ValueError("No se encontró la fila de encabezado esperado (MNUFV / MEMV / TOTAL).")

    header_line = lines[header_idx]
    header_texts = [t for _, t in header_line]
    header_positions = [x for x, _ in header_line]

    # Detectar solo los tokens de encabezado numérico (MNUFV, MEMV, TOTAL)
    # Tomaremos el patrón en el orden que aparezcan en la línea.
    numeric_headers = []
    numeric_positions = []
    for x, t in header_line:
        tu = t.upper()
        if any(k in tu for k in ["MNUFV", "MN+UFV", "MN", "ME", "MEMV", "TOTAL"]):
            # normalizamos el nombre
            if "MNUFV" in tu or "MN+UFV" in tu or re.fullmatch(r"^MN.*", tu):
                numeric_headers.append("MNUFV")
            elif "MEMV" in tu or re.fullmatch(r"^ME.*", tu):
                numeric_headers.append("MEMV")
            elif "TOTAL" in tu:
                numeric_headers.append("TOTAL")
            else:
                numeric_headers.append(tu)
            numeric_positions.append(x)

    if len(numeric_positions) < 3:
        raise ValueError("No se detectaron suficientes columnas numéricas en encabezado.")

    # Si se detectaron repetidos (ej. MNUFV MEMV TOTAL MNUFV MEMV TOTAL), mantenemos el orden completo
    # Construimos bordes (intervalos) entre posiciones para asignar palabras
    # Usamos puntos medios entre columnas adyacentes como límites
    limits = []
    xs = numeric_positions
    # si hay texto antes de la primera columna, definimos left_bound
    left_bound = min([p for p in header_positions]) - 200  # generoso
    # calcular límites medios
    mids = []
    for a, b in zip(xs, xs[1:]):
        mids.append((a + b) / 2.0)
    # límites: [left_bound, mid1, mid2, ..., +inf]
    limits = [left_bound] + mids + [xs[-1] + (xs[-1] - xs[-2] if len(xs) > 1 else 200)]

    # Nombre de columnas resultantes
    col_names = ["CONCEPTO"] + numeric_headers

    structured_rows = []

    # Procesar cada línea por debajo del header
    for line in lines[header_idx + 1:]:
        # obtener texto unido y saltar notas/encabezados repetidos
        joined_txt = " ".join([t for _, t in line]).strip()
        if not joined_txt:
            continue
        jup = joined_txt.upper()
        if any(k in jup for k in ["VARIACIÓN", "NOTA", "EN MILLONES", "SISTEMA DE INTERMEDIACIÓN"]):
            # conservar si es parte de tabla? normalmente saltamos cabeceras/leyendas
            # saltamos leyendas largas
            if re.search(r"^\s*TOTAL|^VARIACIÓN", jup):
                pass  # permitir procesar las filas total que contengan números
            else:
                # si no contiene números, saltar
                if not re.search(r"\d", joined_txt):
                    continue

        # Para cada palabra en la línea, categorizamos por columna según su x0
        # Construimos buckets igual a len(numeric_positions)
        buckets = [""] * len(numeric_positions)
        concept_parts = []
        for x, t in line:
            # si t parece un número o contiene dígitos y está a la derecha, asignar bucket
            # encontrar índice del bucket según limits
            assigned_idx = None
            for idx in range(len(limits) - 1):
                if limits[idx] <= x < limits[idx + 1]:
                    assigned_idx = idx  # idx==0 corresponde a la primera numeric column? adjust below
                    break
            # Si assigned_idx is None, asignar al bucket más cercano:
            if assigned_idx is None:
                distances = [abs(x - px) for px in xs]
                assigned_idx = int(np.argmin(distances))
            # assigned_idx from 0..(n-1) but our buckets map to numeric_positions (0..n-1)
            # Ahora: si x está a la izquierda del primer numeric col, treat as concept text
            if x < xs[0] - 10:
                concept_parts.append(t)
            else:
                # si assigned_idx == 0 but x is still left of xs[0], handled; else place in bucket assigned_idx
                if 0 <= assigned_idx < len(buckets):
                    # concatenar palabras en ese bucket (manteniendo orden)
                    buckets[assigned_idx] = (buckets[assigned_idx] + " " + t).strip() if buckets[assigned_idx] else t

        concepto = " ".join(concept_parts).strip()
        # Si no se capturó concepto por coordenadas, intentar tomar todo texto hasta la primera columna numérica
        if not concepto:
            # tomar palabra(s) con x < limits[1] (el primer límite que separa concepto/primera columna)
            left_words = [t for x, t in line if x < limits[1]]
            if left_words:
                # excluir los tokens que correspondan exactamente a las etiquetas numéricas
                concepto = " ".join(left_words).strip()

            # si sigue vacío, usar primer token
            if not concepto and line:
                concepto = line[0][1]

        # Normalizar cada bucket a número (si aplica) o texto limpio
        normalized = [_clean_text(b) for b in buckets]
        numeric_vals = [_num_from_str(v) for v in normalized]

        row = [concepto] + numeric_vals
        structured_rows.append(row)

    # Armar DataFrame y alinear número de columnas
    if not structured_rows:
        raise ValueError("No se pudo construir ninguna fila estructurada a partir de la página.")

    max_cols = max(len(r) for r in structured_rows)
    # si faltan columnas numéricas en algunas filas, rellenar con NaN
    for r in structured_rows:
        if len(r) < max_cols:
            r.extend([np.nan] * (max_cols - len(r)))

    # construir nombres de columnas finales
    final_numeric_count = max_cols - 1
    # si los headers detectados son menos que final_numeric_count, repetimos los nombres en ciclo
    header_cycle = numeric_headers.copy()
    while len(header_cycle) < final_numeric_count:
        header_cycle += numeric_headers
    final_cols = ["CONCEPTO"] + header_cycle[:final_numeric_count]

    df = pd.DataFrame(structured_rows, columns=final_cols)

    # limpieza final: eliminar filas vacías (sin números)
    df = df.dropna(how="all", subset=final_cols[1:]).reset_index(drop=True)

    # convertir floats con formato de miles si quieres, aquí mantenemos floats; si quieres strings formateadas,
    # puedes aplicar df[c] = df[c].map(lambda v: "{:,.0f}".format(v) if not pd.isna(v) else "")
    if save_excel:
        out_dir = pdf_path.parent.parent / "temp"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{pdf_path.stem}_page{page_number}_asfi_aligned.xlsx"
        # guardamos sin índices
        df.to_excel(out_file, index=False)
        print(f"✅ Tabla estructurada exportada a: {out_file}")

    print(f"✅ Estructuración finalizada — filas: {len(df)}, columnas: {len(df.columns)}")
    return df
