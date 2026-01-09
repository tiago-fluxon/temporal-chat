"""Text file reader with encoding detection."""

from pathlib import Path

import chardet


class TextReadError(Exception):
    """Raised when text file cannot be read."""

    pass


def read_text_file(
    file_path: Path,
    max_size_mb: int = 10,
    encoding: str | None = None,
) -> str:
    """
    Read text file with automatic encoding detection.

    Args:
        file_path: Path to text file
        max_size_mb: Maximum file size in megabytes
        encoding: Explicit encoding (if None, auto-detect)

    Returns:
        File contents as string

    Raises:
        TextReadError: If file cannot be read or is too large
    """
    if not file_path.exists():
        raise TextReadError(f"File does not exist: {file_path}")

    if not file_path.is_file():
        raise TextReadError(f"Path is not a file: {file_path}")

    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > max_size_mb:
        raise TextReadError(f"File too large: {size_mb:.2f}MB (max: {max_size_mb}MB)")

    try:
        if encoding:
            with open(file_path, encoding=encoding) as f:
                content = f.read()
        else:
            with open(file_path, "rb") as f:
                raw_data = f.read()

            detected = chardet.detect(raw_data)
            detected_encoding = detected.get("encoding", "utf-8")

            try:
                content = raw_data.decode(detected_encoding)
            except (UnicodeDecodeError, TypeError):
                # Fallback to UTF-8 replacing invalid characters
                content = raw_data.decode("utf-8", errors="replace")

        return content

    except Exception as e:
        raise TextReadError(f"Failed to read file: {e}")
