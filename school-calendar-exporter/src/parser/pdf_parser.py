from src.parser.base_parser import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """Extract text from PDF files using pdfplumber."""

    def extract_text(self, file_path: str) -> str:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber is required: pip install pdfplumber")

        texts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Try table extraction first (better for structured schedules)
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            row_text = "\t".join(
                                cell if cell is not None else "" for cell in row
                            )
                            texts.append(row_text)
                else:
                    page_text = page.extract_text()
                    if page_text:
                        texts.append(page_text)
                logger.debug(f"PDF page {i + 1} extracted")

        result = "\n".join(texts)
        logger.info(f"PDF extracted: {len(result)} chars from {file_path}")
        return result
