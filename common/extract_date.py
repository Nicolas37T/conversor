import re
import calendar
from typing import Optional

def extract_date(titles: list[str], filename: str) -> str:
    """
    Extrae fecha de los títulos o del nombre del archivo y devuelve formato YYYY-MM-DD.
    Si solo encuentra año y mes, completa con el último día del mes.
    Si no encuentra nada, retorna '1900-01-01'.
    """
    text_to_search = " ".join(titles) + " " + filename  # buscar primero en títulos, luego en el nombre

    patterns = [
        r"(\d{4})[-_](\d{2})[-_](\d{2})",   # 2025-10-23 o 2025_10_23
        r"(\d{8})",                          # 20251023
        r"(\d{2})[-_](\d{2})[-_](\d{4})",   # 23-10-2025 o 23_10_2025
        r"(\d{1,2})/(\d{1,2})/(\d{4})",     # 23/10/2025
        r"(\d{4})[-_](\d{2})"                # YYYY-MM para completar con último día
    ]

    for pattern in patterns:
        match = re.search(pattern, text_to_search)
        if match:
            groups = [int(x) for x in match.groups()]
            if len(groups) == 1:  # YYYYMMDD
                s = groups[0]
                year = int(str(s)[:4])
                month = int(str(s)[4:6])
                day = int(str(s)[6:8])
            elif len(groups) == 2:  # YYYY-MM
                year, month = groups
                day = calendar.monthrange(year, month)[1]
            elif len(groups) == 3:
                if groups[0] > 1900:
                    year, month, day = groups
                else:
                    day, month, year = groups
            else:
                continue

            try:
                return f"{year:04d}-{month:02d}-{day:02d}"
            except:
                continue

    return "1900-01-01"
