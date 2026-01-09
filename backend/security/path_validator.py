"""
Path validation for secure filesystem access.

Guards against:
- Path traversal attacks (../, absolute paths)
- Symlink escapes
- Access outside whitelisted directories
"""

from pathlib import Path


class PathValidationError(Exception):
    """Raised when path validation fails."""

    pass


class PathValidator:
    """Validates paths against whitelist and security rules."""

    def __init__(self, allowed_base: str = "/documents"):
        """
        Initialize validator with allowed base directory.

        Args:
            allowed_base: Base directory that all paths must be within
        """
        self.allowed_base = Path(allowed_base).expanduser().resolve()

    def validate(self, user_path: str) -> Path:
        """
        Validate and resolve path, ensuring it's within allowed base.

        Args:
            user_path: User-provided path (relative or absolute)

        Returns:
            Resolved absolute Path object

        Raises:
            PathValidationError: If path is invalid or outside allowed base
        """
        if not user_path or not user_path.strip():
            raise PathValidationError("Path cannot be empty")

        if "\x00" in user_path:
            raise PathValidationError("Path contains null bytes")

        try:
            # Reject tilde paths - not applicable in container context
            if user_path.startswith("~"):
                raise PathValidationError(
                    "Tilde paths (~) not supported. "
                    "Desktop is already mounted. Use relative paths: "
                    "'/' for Desktop root, or 'subfolder' for subdirectories"
                )

            if user_path == "/":
                full_path = self.allowed_base
            elif not user_path.startswith("/"):
                full_path = self.allowed_base / user_path
            else:
                # Handle absolute paths like /documents/subfolder
                abs_path = Path(user_path)
                try:
                    rel = abs_path.relative_to("/documents")
                    full_path = self.allowed_base / rel
                except ValueError:
                    raise PathValidationError(
                        f"Absolute path '{user_path}' is not within /documents. "
                        "Use relative paths instead"
                    )

            resolved_path = full_path.resolve(strict=False)

        except (ValueError, RuntimeError) as e:
            raise PathValidationError(f"Invalid path format: {e}")

        try:
            resolved_path.relative_to(self.allowed_base)
        except ValueError:
            raise PathValidationError(
                f"Path '{user_path}' is outside allowed directory '{self.allowed_base}'"
            )

        if resolved_path.exists():
            # Re-resolve with strict=True to catch symlinks pointing outside allowed base
            real_path = resolved_path.resolve(strict=True)
            try:
                real_path.relative_to(self.allowed_base)
            except ValueError:
                raise PathValidationError(
                    f"Symlink escape detected: '{user_path}' points to '{real_path}'"
                )

        return resolved_path

    def validate_file(self, user_path: str, max_size_mb: int = 10) -> Path:
        """
        Validate file path and check size limits.

        Args:
            user_path: User-provided file path
            max_size_mb: Maximum allowed file size in megabytes

        Returns:
            Validated Path object

        Raises:
            PathValidationError: If validation fails or file too large
        """
        file_path = self.validate(user_path)

        if not file_path.exists():
            raise PathValidationError(f"File does not exist: '{user_path}'")

        if not file_path.is_file():
            raise PathValidationError(f"Path is not a regular file: '{user_path}'")

        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > max_size_mb:
            raise PathValidationError(f"File too large: {size_mb:.2f}MB (max: {max_size_mb}MB)")

        return file_path

    def validate_directory(self, user_path: str) -> Path:
        """
        Validate directory path.

        Args:
            user_path: User-provided directory path

        Returns:
            Validated Path object

        Raises:
            PathValidationError: If validation fails or not a directory
        """
        dir_path = self.validate(user_path)

        if not dir_path.exists():
            raise PathValidationError(f"Directory does not exist: '{user_path}'")

        if not dir_path.is_dir():
            raise PathValidationError(f"Path is not a directory: '{user_path}'")

        return dir_path
