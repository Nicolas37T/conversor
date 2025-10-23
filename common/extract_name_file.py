from pathlib import Path

def extract_file_name(file_path: str) -> str:
    """
    Devuelve solo el nombre del archivo sin extensión.
    Ejemplo: '2025-04-30_carta informativa.pdf' -> '2025-04-30_carta informativa'
    """
    p = Path(file_path)
    return p.stem
