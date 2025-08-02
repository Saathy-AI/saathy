"""Git commit chunking strategy."""

from typing import Optional

from ..core.models import Chunk, ChunkMetadata
from .base import BaseChunkingStrategy


class GitCommitChunker(BaseChunkingStrategy):
    """Git commit and diff chunking."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.commit_patterns = [
            r"^commit\s+[a-f0-9]{40}",  # Commit hash
            r"^Author:\s+",  # Author line
            r"^Date:\s+",  # Date line
            r"^diff\s+--git",  # Diff start
            r"^---\s+a/",  # File marker
            r"^+++\s+b/",  # File marker
        ]

    def get_strategy_name(self) -> str:
        return "git_commit"

    def _chunk_implementation(
        self, content: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Split git commit into message and diff sections."""
        if len(content) <= self.max_chunk_size:
            return [
                self._create_chunk(
                    content=content,
                    start_index=0,
                    end_index=len(content),
                    chunk_type="git_commit",
                    metadata=metadata,
                )
            ]

        # Split into commit message and diff
        message, diff = self._split_commit_parts(content)

        chunks = []

        # Chunk commit message (semantic)
        if message:
            message_chunks = self._chunk_message(message, metadata)
            chunks.extend(message_chunks)

        # Chunk diff (fixed size)
        if diff:
            diff_chunks = self._chunk_diff(diff, metadata)
            chunks.extend(diff_chunks)

        return chunks

    def _split_commit_parts(self, content: str) -> tuple[str, str]:
        """Split commit content into message and diff parts."""
        lines = content.split("\n")
        message_lines = []
        diff_lines = []
        in_diff = False

        for line in lines:
            if line.startswith("diff --git"):
                in_diff = True

            if in_diff:
                diff_lines.append(line)
            else:
                message_lines.append(line)

        return "\n".join(message_lines), "\n".join(diff_lines)

    def _chunk_message(
        self, message: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Chunk commit message using semantic boundaries."""
        if len(message) <= self.max_chunk_size:
            return [
                self._create_chunk(
                    content=message,
                    start_index=0,
                    end_index=len(message),
                    chunk_type="git_commit",
                    metadata=metadata,
                )
            ]

        # Split by paragraphs
        paragraphs = message.split("\n\n")
        chunks = []
        current_chunk = []
        current_size = 0
        start_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_size = len(paragraph)

            if current_size + paragraph_size > self.max_chunk_size and current_chunk:
                chunk_content = "\n\n".join(current_chunk)
                end_index = start_index + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start_index=start_index,
                        end_index=end_index,
                        chunk_type="git_commit",
                        metadata=metadata,
                    )
                )

                start_index = end_index
                current_chunk = []
                current_size = 0

            current_chunk.append(paragraph)
            current_size += paragraph_size

        # Add final chunk
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk)
            end_index = start_index + len(chunk_content)

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start_index=start_index,
                    end_index=end_index,
                    chunk_type="git_commit",
                    metadata=metadata,
                )
            )

        return chunks

    def _chunk_diff(
        self, diff: str, metadata: Optional[ChunkMetadata] = None
    ) -> list[Chunk]:
        """Chunk diff using fixed size boundaries."""
        if len(diff) <= self.max_chunk_size:
            return [
                self._create_chunk(
                    content=diff,
                    start_index=0,
                    end_index=len(diff),
                    chunk_type="git_commit",
                    metadata=metadata,
                )
            ]

        chunks = []
        start = 0

        while start < len(diff):
            end = start + self.max_chunk_size

            # Try to break at line boundary
            if end < len(diff):
                last_newline = diff.rfind("\n", start, end)
                if last_newline > start:
                    end = last_newline + 1

            chunk_content = diff[start:end].strip()
            if chunk_content:
                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start_index=start,
                        end_index=end,
                        chunk_type="git_commit",
                        metadata=metadata,
                    )
                )

            start = end - self.overlap
            if start >= len(diff):
                break

        return chunks
