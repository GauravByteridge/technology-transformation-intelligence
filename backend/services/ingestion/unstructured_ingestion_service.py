"""
Unstructured Data Ingestion Service.

Handles the ingestion pipeline for unstructured documents:
1. Text extraction from PDFs, DOCX, etc.
2. Document-aware semantic chunking
3. Rich metadata extraction
4. Embedding generation
5. Storage in ChromaDB
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass

import pymupdf
import pandas as pd

from services.embeddings import EmbeddingGenerator
from db.chroma_client import add_embeddings

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A semantic chunk from a document with rich metadata."""
    text: str
    chunk_index: int
    
    # Source metadata
    source_file: str
    source_type: str
    category: str
    
    # Document structure
    page_number: Optional[int] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    
    # For Excel sheets processed as unstructured
    sheet_name: Optional[str] = None
    
    def to_metadata(self) -> dict:
        """Convert to ChromaDB metadata dict."""
        meta = {
            "file_name": self.source_file,
            "source_type": self.source_type,
            "category": self.category,
            "chunk_index": self.chunk_index,
        }
        if self.page_number is not None:
            meta["page_number"] = self.page_number
        if self.section:
            meta["section"] = self.section
        if self.subsection:
            meta["subsection"] = self.subsection
        if self.sheet_name:
            meta["sheet_name"] = self.sheet_name
        return meta


class SemanticChunker:
    """
    Document-aware chunker that respects structural boundaries.
    
    Unlike the simple character-based chunker, this:
    - Splits on natural boundaries (paragraphs, sections, sentences)
    - Preserves headings and structure
    - Uses sentence-aware overlap
    - Targets 500-800 tokens per chunk
    """
    
    # Approximate characters per token (for English)
    CHARS_PER_TOKEN = 4
    
    # Target chunk size in tokens
    MIN_TOKENS = 400
    MAX_TOKENS = 800
    
    # Overlap in sentences
    OVERLAP_SENTENCES = 2
    
    # Patterns for detecting structure
    HEADING_PATTERNS = [
        re.compile(r'^#{1,6}\s+.+$', re.MULTILINE),  # Markdown headers
        re.compile(r'^[A-Z][A-Z\s]{5,}$', re.MULTILINE),  # ALL CAPS headings
        re.compile(r'^\d+\.\s+[A-Z].+$', re.MULTILINE),  # Numbered sections
        re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:$', re.MULTILINE),  # Title Case:
    ]
    
    # Sentence ending pattern
    SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    
    def chunk(self, text: str, source_file: str, source_type: str,
              category: str, sheet_name: Optional[str] = None,
              base_page: int = 1) -> list[DocumentChunk]:
        """
        Split text into semantic chunks with rich metadata.
        
        Args:
            text: The text to chunk
            source_file: Source file name
            source_type: File type (pdf, xlsx, etc.)
            category: File category
            sheet_name: Optional sheet name for Excel
            base_page: Starting page number
            
        Returns:
            List of DocumentChunk objects
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        chunk_index = 0
        
        # First, try to split by major sections
        sections = self._split_into_sections(text)
        
        for section_text, section_name in sections:
            # Split section into paragraphs
            paragraphs = self._split_into_paragraphs(section_text)
            
            current_chunk = []
            current_tokens = 0
            
            for para in paragraphs:
                para_tokens = len(para) // self.CHARS_PER_TOKEN
                
                # If paragraph is too large, split by sentences
                if para_tokens > self.MAX_TOKENS:
                    # Flush current chunk first
                    if current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(DocumentChunk(
                            text=chunk_text,
                            chunk_index=chunk_index,
                            source_file=source_file,
                            source_type=source_type,
                            category=category,
                            section=section_name,
                            sheet_name=sheet_name,
                            page_number=base_page
                        ))
                        chunk_index += 1
                        current_chunk = []
                        current_tokens = 0
                    
                    # Split large paragraph by sentences
                    sentence_chunks = self._split_by_sentences(para)
                    for sent_chunk in sentence_chunks:
                        chunks.append(DocumentChunk(
                            text=sent_chunk,
                            chunk_index=chunk_index,
                            source_file=source_file,
                            source_type=source_type,
                            category=category,
                            section=section_name,
                            sheet_name=sheet_name,
                            page_number=base_page
                        ))
                        chunk_index += 1
                
                # If adding this paragraph would exceed max, flush
                elif current_tokens + para_tokens > self.MAX_TOKENS:
                    if current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(DocumentChunk(
                            text=chunk_text,
                            chunk_index=chunk_index,
                            source_file=source_file,
                            source_type=source_type,
                            category=category,
                            section=section_name,
                            sheet_name=sheet_name,
                            page_number=base_page
                        ))
                        chunk_index += 1
                        
                        # Sentence-aware overlap: keep last sentences
                        last_para = current_chunk[-1] if current_chunk else ""
                        overlap_sentences = self._get_last_sentences(last_para, self.OVERLAP_SENTENCES)
                        current_chunk = [overlap_sentences] if overlap_sentences else []
                        current_tokens = len(overlap_sentences) // self.CHARS_PER_TOKEN if overlap_sentences else 0
                    
                    current_chunk.append(para)
                    current_tokens += para_tokens
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens
            
            # Flush remaining
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                if chunk_text.strip():
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        source_file=source_file,
                        source_type=source_type,
                        category=category,
                        section=section_name,
                        sheet_name=sheet_name,
                        page_number=base_page
                    ))
                    chunk_index += 1
        
        return chunks
    
    def _split_into_sections(self, text: str) -> list[tuple[str, Optional[str]]]:
        """
        Split text into sections based on headings.
        
        Returns:
            List of (section_text, section_name) tuples
        """
        # Find all headings
        heading_positions = []
        for pattern in self.HEADING_PATTERNS:
            for match in pattern.finditer(text):
                heading_positions.append((match.start(), match.end(), match.group().strip()))
        
        if not heading_positions:
            return [(text, None)]
        
        # Sort by position
        heading_positions.sort(key=lambda x: x[0])
        
        sections = []
        
        # Text before first heading
        if heading_positions[0][0] > 0:
            sections.append((text[:heading_positions[0][0]].strip(), None))
        
        # Each section
        for i, (start, end, heading) in enumerate(heading_positions):
            next_start = heading_positions[i + 1][0] if i + 1 < len(heading_positions) else len(text)
            section_text = text[end:next_start].strip()
            if section_text:
                sections.append((section_text, heading))
        
        return sections if sections else [(text, None)]
    
    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines or more
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_by_sentences(self, text: str) -> list[str]:
        """Split text into sentence-based chunks."""
        sentences = self.SENTENCE_END.split(text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sent_tokens = len(sentence) // self.CHARS_PER_TOKEN
            
            if current_tokens + sent_tokens > self.MAX_TOKENS and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Overlap
                current_chunk = current_chunk[-self.OVERLAP_SENTENCES:] if len(current_chunk) > self.OVERLAP_SENTENCES else []
                current_tokens = sum(len(s) // self.CHARS_PER_TOKEN for s in current_chunk)
            
            current_chunk.append(sentence)
            current_tokens += sent_tokens
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _get_last_sentences(self, text: str, n: int) -> str:
        """Get the last n sentences from text."""
        sentences = self.SENTENCE_END.split(text)
        if len(sentences) <= n:
            return text
        return " ".join(sentences[-n:])


class UnstructuredIngestionService:
    """
    Handles ingestion of unstructured documents into ChromaDB.
    
    Features:
    - PDF text extraction with page tracking
    - Excel sheet text extraction for unstructured sheets
    - Semantic chunking with structure preservation
    - Rich metadata for better retrieval
    """
    
    def __init__(self):
        self.chunker = SemanticChunker()
        self.embedding_generator = EmbeddingGenerator()
    
    def ingest_pdf(self, file_id: int, file_path: str, 
                   file_name: str, category: str) -> int:
        """
        Ingest a PDF document.
        
        Returns:
            Number of chunks created
        """
        chunks = []
        chunk_index = 0
        
        with pymupdf.open(file_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text()
                if not page_text or not page_text.strip():
                    continue
                
                # Chunk the page text
                page_chunks = self.chunker.chunk(
                    text=page_text,
                    source_file=file_name,
                    source_type="pdf",
                    category=category,
                    base_page=page_num
                )
                
                # Update chunk indices for global ordering
                for chunk in page_chunks:
                    chunk.chunk_index = chunk_index
                    chunk.page_number = page_num
                    chunk_index += 1
                
                chunks.extend(page_chunks)
        
        if not chunks:
            return 0
        
        # Generate embeddings and store
        return self._store_chunks(file_id, chunks)
    
    def ingest_excel_sheet_as_text(self, file_id: int, file_path: str,
                                   file_name: str, sheet_name: str,
                                   category: str) -> int:
        """
        Ingest an Excel sheet as unstructured text.
        
        Used for sheets that are classified as unstructured (notes, descriptions, etc.)
        
        Returns:
            Number of chunks created
        """
        excel_file = pd.ExcelFile(file_path)
        
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            text = f"Sheet: {sheet_name}\n\n{df.to_string(index=False)}"
        finally:
            excel_file.close()
        
        chunks = self.chunker.chunk(
            text=text,
            source_file=file_name,
            source_type="xlsx",
            category=category,
            sheet_name=sheet_name
        )
        
        if not chunks:
            return 0
        
        return self._store_chunks(file_id, chunks)
    
    def ingest_text(self, file_id: int, text: str, file_name: str,
                    source_type: str, category: str) -> int:
        """
        Ingest plain text content.
        
        Returns:
            Number of chunks created
        """
        chunks = self.chunker.chunk(
            text=text,
            source_file=file_name,
            source_type=source_type,
            category=category
        )
        
        if not chunks:
            return 0
        
        return self._store_chunks(file_id, chunks)
    
    def _store_chunks(self, file_id: int, chunks: list[DocumentChunk]) -> int:
        """Store chunks in ChromaDB with embeddings."""
        if not chunks:
            return 0
        
        # Prepare data for ChromaDB
        ids = [f"{file_id}_{chunk.chunk_index}" for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {**chunk.to_metadata(), "file_id": file_id}
            for chunk in chunks
        ]
        
        # Generate embeddings
        embeddings = self.embedding_generator.generate(documents)
        
        # Store in ChromaDB
        add_embeddings(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return len(chunks)
