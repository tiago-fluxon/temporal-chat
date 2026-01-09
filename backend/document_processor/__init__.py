"""Document processors for text, PDF, and image files."""

from .pdf_reader import PDFReadError, read_pdf_file
from .text_reader import TextReadError, read_text_file


__all__ = [
    "PDFReadError",
    "TextReadError",
    "read_pdf_file",
    "read_text_file",
]
