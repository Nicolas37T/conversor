import pandas as pd
from extract_title.soat import extract_titles
from common.extract_date import extract_date

from extract_table.soat import extract_table_from_pdf

def build_flat_table(df_raw: pd.DataFrame, titles: dict, pdf_file: str, date_str: str) -> list:
    rows = []
    department_col, use_col = 0, 1
    vehicle_cols = list(range(2, len(df_raw.columns)))
    for i, row in df_raw.iterrows():
        if i == 0:
            continue
        dept = str(row[department_col]).strip()
        use = str(row[use_col]).strip()
        if dept == "" and use == "":
            continue
        for col_idx in vehicle_cols:
            vehicle = df_raw.iloc[0, col_idx].replace("\n", " / ").strip()
            if not vehicle:
                continue
            value = str(row[col_idx]).strip()
            if value.lower() in ["none", "nan"]:
                value = ""
            row_data = {"file": pdf_file}
            row_data.update(titles)
            row_data.update({
                "nv1": dept,
                "nv2": use,
                "nv3": vehicle,
                "date": date_str,
                "value": value
            })
            rows.append(row_data)
    return rows

def clean_service_logic(df_temp: pd.DataFrame, titles: dict) -> pd.DataFrame:
    service_labels = ['SERVICIO PARTICULAR', 'SERVICIO PÚBLICO', 'servicio particular', 'servicio público']
    current_service = None
    clean_rows = []
    for _, row in df_temp.iterrows():
        nv1, nv2, nv3, value = row['nv1'], row['nv2'], row['nv3'], row['value']
        if 'uso' in nv3.lower() and value in service_labels:
            current_service = value
            continue
        nv1_fixed, nv2_fixed = nv1, nv2
        if nv2.upper().startswith('TOTAL '):
            dept_name = nv2[6:].strip()
            nv1_fixed, nv2_fixed = dept_name, 'TOTAL'
        elif nv1.upper().startswith('TOTAL '):
            dept_name = nv1[6:].strip()
            nv1_fixed, nv2_fixed = dept_name, 'TOTAL'
        elif nv2 == '':
            nv2_fixed = current_service if current_service else nv2
        clean_row = {'file': row['file']}
        for title_key in titles.keys():
            clean_row[title_key] = row.get(title_key, '')
        clean_row.update({
            'nv1': nv1_fixed,
            'nv2': nv2_fixed,
            'nv3': nv3,
            'date': row['date'],
            'value': value
        })
        clean_rows.append(clean_row)
    return pd.DataFrame(clean_rows)

def process_pdf_to_long_format(pdf_path, page_number: int, extractor: str = "SOAT") -> pd.DataFrame:
    """
    pdf_path: str o Path
    """
    from pathlib import Path
    pdf_path = Path(pdf_path)  # asegura que sea Path

    # Extraer títulos
    titles = extract_titles(pdf_path, page_number, max_titles=5)
    titles_dict = {f"title_{i+1}": t for i, t in enumerate(titles)}

    # Extraer fecha
    fecha_detectada = extract_date(titles, pdf_path.name)

    # Extraer tabla
    df_raw = extract_table_from_pdf(str(pdf_path), page_number)

    # Construir tabla plana
    rows = build_flat_table(df_raw, titles_dict, pdf_path.name, fecha_detectada)
    df_temp = pd.DataFrame(rows)

    # Limpiar tabla
    df_final = clean_service_logic(df_temp, titles_dict)
    df_final['date'] = "'" + df_final['date'].astype(str)

    # Reordenar columnas
    final_cols = ["file"] + sorted(titles_dict.keys()) + ["nv1", "nv2", "nv3", "date", "value"]
    df_final = df_final[final_cols]

    return df_final
