"""PDF file reader with text extraction."""

from pathlib import Path

import pdfplumber
import pypdf


class PDFReadError(Exception):
    """Raised when PDF cannot be read."""

    pass


def read_pdf_file(
    file_path: Path,
    max_size_mb: int = 10,
    use_pdfplumber_fallback: bool = True,
) -> str:
    """
    Read and extract text from PDF file.

    Args:
        file_path: Path to PDF file
        max_size_mb: Maximum file size in megabytes
        use_pdfplumber_fallback: If True, use pdfplumber if pypdf fails

    Returns:
        Extracted text content

    Raises:
        PDFReadError: If PDF cannot be read or is too large
    """
    if not file_path.exists():
        raise PDFReadError(f"File does not exist: {file_path}")

    if not file_path.is_file():
        raise PDFReadError(f"Path is not a file: {file_path}")

    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > max_size_mb:
        raise PDFReadError(f"PDF too large: {size_mb:.2f}MB (max: {max_size_mb}MB)")

    # Try pypdf first because it's faster
    try:
        text_parts = []

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)

            if reader.is_encrypted:
                raise PDFReadError("PDF is encrypted")

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{text}")
                except Exception as e:
                    # Log page error but continue processing remaining pages
                    text_parts.append(f"--- Page {page_num} ---\n[Error extracting text: {e}]")

        extracted_text = "\n\n".join(text_parts)

        if not extracted_text.strip():
            if use_pdfplumber_fallback:
                return _read_pdf_with_pdfplumber(file_path)
            else:
                raise PDFReadError("No text extracted from PDF")

        return extracted_text

    except PDFReadError:
        raise
    except Exception as e:
        if use_pdfplumber_fallback:
            try:
                return _read_pdf_with_pdfplumber(file_path)
            except Exception as fallback_error:
                raise PDFReadError(
                    f"Failed with both pypdf ({e}) and pdfplumber ({fallback_error})"
                )
        else:
            raise PDFReadError(f"Failed to read PDF: {e}")


def _read_pdf_with_pdfplumber(file_path: Path) -> str:
    """
    Read PDF using pdfplumber (fallback method).

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text content

    Raises:
        PDFReadError: If extraction fails
    """
    try:
        text_parts = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{text}")
                except Exception as e:
                    text_parts.append(f"--- Page {page_num} ---\n[Error: {e}]")

        extracted_text = "\n\n".join(text_parts)

        if not extracted_text.strip():
            raise PDFReadError("No text extracted (pdfplumber)")

        return extracted_text

    except PDFReadError:
        raise
    except Exception as e:
        raise PDFReadError(f"pdfplumber extraction failed: {e}")
