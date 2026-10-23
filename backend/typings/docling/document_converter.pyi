from pathlib import Path
from typing import Any

class DoclingDocument:
    pages: list[Any]
    def save_as_docx(self, path: str | Path) -> None: ...
    def save_as_xlsx(self, path: str | Path) -> None: ...

class ConversionResult:
    document: DoclingDocument

class DocumentConverter:
    def __init__(self, **kwargs: Any) -> None: ...
    def convert(self, source: str | Path) -> ConversionResult: ...
