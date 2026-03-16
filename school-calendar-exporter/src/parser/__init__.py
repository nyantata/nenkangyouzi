from pathlib import Path

from src.parser.base_parser import BaseParser
from src.parser.excel_parser import ExcelParser
from src.parser.pdf_parser import PDFParser


def get_parser(file_path: str) -> BaseParser:
    """Return the appropriate parser based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return PDFParser()
    if ext in (".xlsx", ".xls", ".csv"):
        return ExcelParser()
    raise ValueError(f"Unsupported file format: {ext}")
