"""
Temporal activities for document discovery and reading.

These activities handle filesystem operations and are executed by Temporal workers.
"""

from dataclasses import dataclass
from pathlib import Path

from temporalio import activity

from backend.document_processor import (
    PDFReadError,
    TextReadError,
    read_pdf_file,
    read_text_file,
)
from backend.security import PathValidator


@dataclass
class Document:
    """Represents a processed document."""

    path: str
    filename: str
    content: str
    file_type: str
    size_bytes: int
    error: str = ""


@activity.defn
async def scan_directory(
    user_path: str,
    allowed_extensions: list[str] = None,
    max_total_size_mb: int = 100,
) -> list[str]:
    """
    Scan directory for files matching allowed extensions.

    Args:
        user_path: User-provided directory path (relative to /documents)
        allowed_extensions: List of allowed extensions (e.g., ['.txt', '.pdf'])
        max_total_size_mb: Maximum total size to scan

    Returns:
        List of file paths (relative to /documents)

    Raises:
        PathValidationError: If path is invalid or outside allowed directory
    """
    if allowed_extensions is None:
        allowed_extensions = [".txt", ".md", ".pdf", ".json", ".csv"]

    validator = PathValidator(allowed_base="/documents")
    dir_path = validator.validate_directory(user_path)

    activity.logger.info(f"Scanning directory: {dir_path}")

    files = []
    total_size = 0

    try:
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in allowed_extensions:
                continue

            file_size = file_path.stat().st_size
            size_mb = total_size / (1024 * 1024)

            if size_mb + (file_size / (1024 * 1024)) > max_total_size_mb:
                activity.logger.warning(
                    f"Reached max total size ({max_total_size_mb}MB), stopping scan"
                )
                break

            total_size += file_size

            relative_path = str(file_path.relative_to(Path("/documents")))
            files.append(relative_path)

            # Heartbeat every 10 files to avoid queue overflow
            if len(files) % 10 == 0:
                activity.heartbeat()

    except Exception as e:
        activity.logger.error(f"Error scanning directory: {e}")
        raise

    activity.logger.info(f"Found {len(files)} files ({total_size / (1024 * 1024):.2f}MB)")
    return files


@activity.defn
async def read_document(file_path: str, max_size_mb: int = 10) -> Document:
    """
    Read document content based on file type.

    Args:
        file_path: File path (relative to /documents)
        max_size_mb: Maximum file size in megabytes

    Returns:
        Document object with content or error message

    Raises:
        PathValidationError: If path is invalid
    """
    validator = PathValidator(allowed_base="/documents")
    validated_path = validator.validate_file(file_path, max_size_mb)

    activity.logger.info(f"Reading document: {validated_path}")

    filename = validated_path.name
    file_type = validated_path.suffix.lower()
    size_bytes = validated_path.stat().st_size

    try:
        if file_type in [".txt", ".md", ".json", ".csv"]:
            content = read_text_file(validated_path, max_size_mb)
            return Document(
                path=file_path,
                filename=filename,
                content=content,
                file_type=file_type,
                size_bytes=size_bytes,
            )

        elif file_type == ".pdf":
            content = read_pdf_file(validated_path, max_size_mb)
            return Document(
                path=file_path,
                filename=filename,
                content=content,
                file_type=file_type,
                size_bytes=size_bytes,
            )

        else:
            return Document(
                path=file_path,
                filename=filename,
                content="",
                file_type=file_type,
                size_bytes=size_bytes,
                error=f"Unsupported file type: {file_type}",
            )

    except (TextReadError, PDFReadError) as e:
        activity.logger.error(f"Error reading {filename}: {e}")
        return Document(
            path=file_path,
            filename=filename,
            content="",
            file_type=file_type,
            size_bytes=size_bytes,
            error=str(e),
        )

    except Exception as e:
        activity.logger.error(f"Unexpected error reading {filename}: {e}")
        return Document(
            path=file_path,
            filename=filename,
            content="",
            file_type=file_type,
            size_bytes=size_bytes,
            error=f"Unexpected error: {e}",
        )
