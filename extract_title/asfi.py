
from pathlib import Path
import pdfplumber
import re

def extract_asfi_title(pdf_path: Path, page_number: int, max_lines: int = 5) -> str:
    pdf_path = Path(pdf_path)
    with pdfplumber.open(pdf_path) as pdf:
        if page_number > len(pdf.pages):
            raise ValueError(f"❌ El PDF solo tiene {len(pdf.pages)} páginas.")
        page = pdf.pages[page_number - 1]

        # Extraer texto por líneas con coordenadas
        words = page.extract_words(use_text_flow=True)
        if not words:
            return "TÍTULO NO DETECTADO"

        # Agrupar por línea según la coordenada Y (más pequeña = más arriba)
        lines_dict = {}
        for w in words:
            y = round(w["top"], 1)
            lines_dict.setdefault(y, []).append(w["text"])

        # Ordenar de arriba hacia abajo
        sorted_lines = sorted(lines_dict.items(), key=lambda x: x[0])

        # Tomar las primeras líneas de la parte superior (antes de tablas o números densos)
        title_lines = []
        for _, parts in sorted_lines:
            line_text = " ".join(parts).strip()
            # Saltar líneas vacías
            if not line_text:
                continue
            # Si detectamos que la línea parece tabular (muchos números), paramos
            if re.search(r"\d{2,}", line_text) and len(re.findall(r"\d", line_text)) > len(line_text) * 0.3:
                break
            # Agregar línea si es corta (típicamente un título)
            title_lines.append(line_text)
            if len(title_lines) >= max_lines:
                break

        # Combinar líneas encontradas
        title = " — ".join(title_lines).strip()
        return title or "TÍTULO NO DETECTADO"
