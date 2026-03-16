from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Common interface for all file parsers."""

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extract plain text from *file_path* and return it as a string."""
        ...
