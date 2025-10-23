"""
extract_titles.py

Versión mejorada:
Devuelve una LISTA de títulos detectados en la parte superior de la página PDF.
Cada título es una línea de texto (útil para columnas de Excel: titulo_1, titulo_2, etc.)
"""

from typing import List
import fitz
import re
import math


def _clean_text(s: str) -> str:
    s = s.replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_titles(pdf_path: str, page_number: int, max_titles: int = 5) -> List[str]:
    """
    Extrae hasta 'max_titles' líneas de título de la parte superior de la página PDF.
    Devuelve una lista ordenada de strings.
    """
    try:
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"El PDF tiene {len(doc)} páginas; pediste la {page_number}.")

        page = doc[page_number - 1]
        page_dict = page.get_text("dict")
        blocks = page_dict.get("blocks", [])

        spans = []
        for b in blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text = _clean_text(span.get("text", ""))
                    if not text:
                        continue
                    if len(re.sub(r"[^\wÁÉÍÓÚÑáéíóúñ]", "", text)) < 3:
                        continue
                    size = float(span.get("size", 0))
                    bbox = span.get("bbox", [0, 0, 0, 0])
                    spans.append({
                        "text": text,
                        "size": size,
                        "y0": float(bbox[1]),
                        "x0": float(bbox[0]),
                    })

        if not spans:
            raw = page.get_text("text").strip()
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            return lines[:max_titles]

        page_height = page.rect.height
        top_limit = page_height * 0.55  # considerar parte superior de la página
        top_spans = [s for s in spans if s["y0"] <= top_limit]

        if not top_spans:
            top_spans = spans

        # Agrupar spans en líneas según coordenada Y
        top_spans.sort(key=lambda s: (s["y0"], s["x0"]))
        lines = []
        y_tol = 3.0
        for s in top_spans:
            if not lines:
                lines.append([s])
                continue
            last = lines[-1][-1]
            if abs(s["y0"] - last["y0"]) <= y_tol:
                lines[-1].append(s)
            else:
                lines.append([s])

        # Construir texto por línea
        line_texts = []
        for ln in lines:
            ln_sorted = sorted(ln, key=lambda x: x["x0"])
            full_line = " ".join(t["text"] for t in ln_sorted)
            if not full_line:
                continue

            avg_size = sum(s["size"] for s in ln_sorted) / len(ln_sorted)
            num_ratio = sum(c.isdigit() for c in full_line) / max(1, len(full_line))
            if num_ratio > 0.25:
                continue  # probablemente tabla
            if avg_size < 6:
                continue  # texto pequeño, no título

            line_texts.append({
                "y": ln_sorted[0]["y0"],
                "text": _clean_text(full_line),
                "score": avg_size + len(full_line) / 10.0,
            })

        # Ordenar por posición (de arriba a abajo)
        line_texts.sort(key=lambda x: x["y"])

        # Filtrar duplicados o líneas vacías
        unique_titles = []
        for lt in line_texts:
            if lt["text"] not in unique_titles:
                unique_titles.append(lt["text"])

        # Limitar a máximo N títulos y pasar a mayúsculas limpias
        titles = [t.upper() for t in unique_titles[:max_titles]]

        return titles or ["Sin texto detectado"]

    except Exception as e:
        return [f"⚠️ Error extrayendo títulos: {e}"]
