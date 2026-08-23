"""
Text chunking implementation for the document ingestion pipeline.

Provides a fixed-size character chunking strategy with configurable overlap,
page boundary tracking using PAGE_BREAK delimiters, and section heading
detection from markdown-style headers.

Satisfies the TextChunker protocol.
"""

from __future__ import annotations

import re

from app.documents.pipeline import ChunkResult
from app.errors.document_errors import ChunkingError

# Delimiter used to mark page boundaries in extracted text
PAGE_BREAK_DELIMITER = "\n---PAGE_BREAK---\n"


class FixedSizeChunker:
    """Splits text into fixed-size character chunks with overlap.

    Tracks page boundaries (delimited by PAGE_BREAK_DELIMITER) and section
    headings (markdown-style lines starting with #). Each chunk is annotated
    with the page_number and section it belongs to.

    Satisfies the TextChunker protocol via structural subtyping.
    """

    def chunk(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[ChunkResult]:
        """Split text into chunks with page boundary and section tracking.

        Args:
            text: Full text content to split. May contain PAGE_BREAK delimiters
                  and markdown-style headings.
            chunk_size: Target number of characters per chunk. Must be >= 1.
            overlap: Number of overlapping characters between consecutive chunks.
                     Must be >= 0. Capped at chunk_size - 1 if too large.

        Returns:
            Ordered list of ChunkResult instances with chunk_index, page_number,
            and section populated.

        Raises:
            ChunkingError: If chunk_size < 1 or overlap < 0.
        """
        if chunk_size < 1:
            raise ChunkingError(
                file_name="<unknown>",
                message=f"chunk_size must be >= 1, got {chunk_size}",
            )
        if overlap < 0:
            raise ChunkingError(
                file_name="<unknown>",
                message=f"overlap must be >= 0, got {overlap}",
            )

        if not text:
            return []

        # Cap overlap at chunk_size - 1
        effective_overlap = min(overlap, chunk_size - 1) if chunk_size > 1 else 0
        step = max(chunk_size - effective_overlap, 1)

        # Build a position-to-page map and position-to-section map
        page_breaks = self._find_page_breaks(text)
        section_positions = self._find_section_headings(text)

        # Remove page break delimiters from the text for chunking purposes
        clean_text = text.replace(PAGE_BREAK_DELIMITER, "")

        # Build mapping from clean_text positions to page numbers
        page_map = self._build_page_map(text, clean_text)

        # Build mapping from clean_text positions to section headings
        section_map = self._build_section_map(text, clean_text)

        if not clean_text:
            return []

        chunks: list[ChunkResult] = []
        start = 0
        chunk_index = 0

        while start < len(clean_text):
            end = start + chunk_size
            chunk_text = clean_text[start:end]

            # Determine page_number for this chunk's start position
            page_number = self._get_page_at_position(start, page_map)

            # Determine section for this chunk's start position
            section = self._get_section_at_position(start, section_map)

            chunks.append(
                ChunkResult(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    section=section,
                )
            )

            chunk_index += 1
            start += step

        return chunks

    def _find_page_breaks(self, text: str) -> list[int]:
        """Find positions of page break delimiters in the original text.

        Returns:
            List of character positions where PAGE_BREAK_DELIMITER starts.
        """
        positions: list[int] = []
        search_start = 0
        while True:
            pos = text.find(PAGE_BREAK_DELIMITER, search_start)
            if pos == -1:
                break
            positions.append(pos)
            search_start = pos + len(PAGE_BREAK_DELIMITER)
        return positions

    def _find_section_headings(self, text: str) -> list[tuple[int, str]]:
        """Find markdown-style section headings in the text.

        Matches lines starting with one or more # characters followed by text.

        Returns:
            List of (position_in_original_text, heading_text) tuples.
        """
        headings: list[tuple[int, str]] = []
        # Match lines beginning with # (markdown headings)
        for match in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
            headings.append((match.start(), match.group(2).strip()))
        return headings

    def _build_page_map(self, original_text: str, clean_text: str) -> list[tuple[int, int]]:
        """Build a mapping from clean_text positions to page numbers.

        Returns a sorted list of (clean_text_position, page_number) tuples
        indicating where each new page starts in the cleaned text.
        """
        # Split by page break delimiter to determine page boundaries
        pages = original_text.split(PAGE_BREAK_DELIMITER)

        page_map: list[tuple[int, int]] = []
        clean_offset = 0

        for page_idx, page_content in enumerate(pages):
            # Remove page breaks from page_content to get its clean length
            # (page_content doesn't contain PAGE_BREAK_DELIMITER itself since we split on it)
            page_map.append((clean_offset, page_idx + 1))
            clean_offset += len(page_content)

        return page_map

    def _build_section_map(
        self, original_text: str, clean_text: str
    ) -> list[tuple[int, str]]:
        """Build a mapping from clean_text positions to section headings.

        Returns a sorted list of (clean_text_position, section_name) tuples.
        """
        headings = self._find_section_headings(original_text)
        if not headings:
            return []

        section_map: list[tuple[int, str]] = []

        for orig_pos, heading_text in headings:
            # Calculate how many page break delimiters appear before this position
            # to determine the offset adjustment
            preceding_text = original_text[:orig_pos]
            delimiter_count = preceding_text.count(PAGE_BREAK_DELIMITER)
            delimiter_total_len = delimiter_count * len(PAGE_BREAK_DELIMITER)
            clean_pos = orig_pos - delimiter_total_len
            section_map.append((clean_pos, heading_text))

        return sorted(section_map, key=lambda x: x[0])

    def _get_page_at_position(
        self, position: int, page_map: list[tuple[int, int]]
    ) -> int:
        """Get the page number for a given position in the clean text.

        Args:
            position: Character position in clean_text.
            page_map: Sorted list of (start_position, page_number).

        Returns:
            Page number (1-based).
        """
        page_number = 1
        for start_pos, page_num in page_map:
            if start_pos <= position:
                page_number = page_num
            else:
                break
        return page_number

    def _get_section_at_position(
        self, position: int, section_map: list[tuple[int, str]]
    ) -> str | None:
        """Get the most recent section heading for a given position.

        Args:
            position: Character position in clean_text.
            section_map: Sorted list of (start_position, section_name).

        Returns:
            Section heading string, or None if no heading precedes this position.
        """
        section: str | None = None
        for start_pos, heading in section_map:
            if start_pos <= position:
                section = heading
            else:
                break
        return section
