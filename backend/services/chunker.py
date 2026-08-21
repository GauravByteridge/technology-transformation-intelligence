"""Chunker service for splitting text into overlapping segments.

Splits extracted text into chunks of 800-1000 characters with configurable
overlap between adjacent chunks to preserve context at boundaries.
"""


class Chunker:
    """Splits text into overlapping chunks suitable for embedding and vector storage.

    Args:
        chunk_size: Target size of each chunk in characters. Must be between 800 and 1000.
                    Defaults to 900.
        overlap: Number of characters to overlap between adjacent chunks.
                 Must be less than chunk_size. Defaults to 100.
    """

    def __init__(self, chunk_size: int = 900, overlap: int = 100):
        if chunk_size < 800 or chunk_size > 1000:
            raise ValueError("chunk_size must be between 800 and 1000")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        """Split text into overlapping chunks of 800-1000 characters.

        Produces segments where each chunk (except possibly the last) has length
        equal to chunk_size. Adjacent chunks share `overlap` characters of content
        to preserve context across boundaries.

        Args:
            text: The input text to split into chunks.

        Returns:
            A list of text chunks. Returns an empty list if the input text is empty
            or contains only whitespace. Returns a single-element list if the text
            is shorter than or equal to chunk_size.
        """
        if not text or not text.strip():
            return []

        # If text is shorter than or equal to chunk_size, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        step = self.chunk_size - self.overlap
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # Only add non-empty chunks
            if chunk.strip():
                chunks.append(chunk)

            # If we've reached the end of the text, stop
            if end >= len(text):
                break

            start += step

        return chunks
