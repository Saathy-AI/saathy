"""Hash utilities for content caching."""

import hashlib
from typing import Optional

from ..core.models import ContentType


def generate_content_hash(
    content: str,
    content_type: Optional[ContentType] = None,
    file_extension: Optional[str] = None,
    max_chunk_size: int = 512,
    overlap: int = 50,
) -> str:
    """Generate hash for content caching."""
    # Use first 1000 characters for performance
    content_sample = content[:1000]

    # Create hash input string
    hash_input = (
        f"{content_sample}_{content_type}_{file_extension}_{max_chunk_size}_{overlap}"
    )

    # Generate MD5 hash
    return hashlib.md5(hash_input.encode()).hexdigest()


def generate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """Generate hash for file content."""
    hash_md5 = hashlib.md5()

    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        # Return hash of file path if file cannot be read
        return hashlib.md5(file_path.encode()).hexdigest()
