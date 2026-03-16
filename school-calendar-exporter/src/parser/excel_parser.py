import csv
import io

from src.parser.base_parser import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExcelParser(BaseParser):
    """Extract text from Excel (.xlsx/.xls) or CSV files."""

    def extract_text(self, file_path: str) -> str:
        lower = file_path.lower()
        if lower.endswith(".csv"):
            return self._from_csv(file_path)
        return self._from_excel(file_path)

    def _from_excel(self, file_path: str) -> str:
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required: pip install openpyxl")

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        lines: list[str] = []
        for sheet in wb.worksheets:
            lines.append(f"[シート: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(c.strip() for c in cells):
                    lines.append("\t".join(cells))
        result = "\n".join(lines)
        logger.info(f"Excel extracted: {len(result)} chars from {file_path}")
        return result

    def _from_csv(self, file_path: str) -> str:
        lines: list[str] = []
        with open(file_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if any(cell.strip() for cell in row):
                    lines.append("\t".join(row))
        result = "\n".join(lines)
        logger.info(f"CSV extracted: {len(result)} chars from {file_path}")
        return result
