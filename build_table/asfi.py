from pathlib import Path
import pandas as pd
import re
from extract_title.asfi import extract_asfi_title
from extract_table.asfi import extract_asfi_table
from common.extract_date import extract_date


def _is_section_header(text: str) -> bool:
    """Heurística simple para detectar encabezados de sección"""
    if not isinstance(text, str) or not text.strip():
        return False
    s = text.strip()
    if len(re.findall(r"\d", s)) > len(s) * 0.2:
        return False
    if re.search(r"\(A\)|\(B\)|TOTAL|DISPONIBILIDADES|INVERSIONES|PREVISION", s, re.IGNORECASE):
        return True
    if s.isupper() and len(s) <= 60:
        return True
    return False


def build_flat_table_asfi(df_raw: pd.DataFrame, titles: list, pdf_file: str, date_str: str,
                          unit: str = "En millones de bolivianos") -> pd.DataFrame:
    rows = []
    pdf_name = str(pdf_file)
    titulo1 = titles[0] if titles else ""
    value_cols = [c for c in df_raw.columns if c.upper() != "CONCEPTO"]

    current_section, current_group = "", ""

    for _, row in df_raw.iterrows():
        concepto = str(row.get("CONCEPTO", "")).strip()
        if concepto == "" and row[value_cols].isna().all().all():
            continue

        if _is_section_header(concepto):
            current_section = concepto
            continue

        if concepto.isupper() and len(concepto) < 60:
            current_group = concepto
            continue

        for col in value_cols:
            raw_val = row.get(col, "")

            # ✅ chequeo robusto
            if isinstance(raw_val, (pd.Series, list, tuple)):
                if all(pd.isna(v) for v in raw_val):
                    continue
            else:
                if raw_val is None or (isinstance(raw_val, float) and pd.isna(raw_val)) or \
                        str(raw_val).strip().lower() in ["nan", "none", ""]:
                    continue

            val = raw_val
            if isinstance(raw_val, str):
                t = raw_val.strip()
                t = re.sub(r"[^\d\-\.,\(\)]", "", t)
                if re.match(r"^\(.*\)$", t):
                    t = "-" + t[1:-1]
                try:
                    val = float(t.replace(".", "").replace(",", "."))
                except Exception:
                    val = t

            rows.append({
                "file": pdf_name,
                "titulo1": titulo1,
                "nv1": current_section,
                "nv2": concepto,
                "nv3": current_group,
                "nv4": str(col),
                "nv5": unit,
                "fecha": date_str,
                "valor": val
            })

    df_final = pd.DataFrame(rows)
    final_cols = ["file", "titulo1", "nv1", "nv2", "nv3", "nv4", "nv5", "fecha", "valor"]
    for c in final_cols:
        if c not in df_final.columns:
            df_final[c] = ""
    df_final = df_final[final_cols]
    return df_final


def process_pdf_to_long_format(pdf_path, page_number: int, extractor: str = "ASFI") -> pd.DataFrame:
    pdf_path = Path(pdf_path)
    titulo = extract_asfi_title(pdf_path, page_number)
    titles = [titulo] if titulo else []

    try:
        fecha_detectada = extract_date(titles, pdf_path.name)
    except Exception:
        m = re.search(r"(\d{2}/\d{2}/\d{4})", titulo)
        fecha_detectada = m.group(1) if m else ""

    df_raw = extract_asfi_table(pdf_path, page_number, save_temp=True)
    df_final = build_flat_table_asfi(df_raw, titles, pdf_path.name, fecha_detectada)

    if fecha_detectada and re.match(r"\d{2}/\d{2}/\d{4}", fecha_detectada):
        dd, mm, yyyy = fecha_detectada.split("/")
        df_final["fecha"] = f"{yyyy}-{mm}-{dd}"

    return df_final
