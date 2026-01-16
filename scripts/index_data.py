"""Script to index therapy documents into Supabase."""

from __future__ import annotations

import asyncio
import sys
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.core.config import get_settings
from src.core.database import get_database
from src.services.embedding_service import get_embedding_service
from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class DocumentChunk:
    """Represents a chunk of text with metadata."""

    content: str
    metadata: dict


@dataclass
class PageText:
    """Text from a single page with page number."""

    page_num: int
    text: str


def infer_topic_from_filename(filename: str) -> str:
    """Infer topic from PDF filename."""
    filename_lower = filename.lower()
    topic_keywords = {
        "depression": ["depression", "depressive"],
        "anxiety": ["anxiety", "anxious"],
        "stress": ["stress", "stressed"],
        "cbt": ["cbt", "cognitive", "behavioral"],
        "breathing": ["breathing", "breath", "breathinig"],
        "visualization": ["visualization", "visualisation"],
        "therapy": ["therapy", "therapist", "therapeutic"],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in filename_lower for keyword in keywords):
            return topic

    return "general"


def infer_document_type(filename: str) -> str:
    """Infer document type from filename."""
    filename_lower = filename.lower()

    if "guide" in filename_lower or "manual" in filename_lower:
        return "guide"
    if "treatment" in filename_lower or "management" in filename_lower:
        return "guideline"
    if "how-to" in filename_lower:
        return "technique"
    if any(keyword in filename_lower for keyword in ["978924", "who", "nice"]):
        return "guideline"
    return "resource"


def chunk_text_by_characters(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Chunk text using character-based slicing (memory-efficient).
    
    Args:
        text: Text to chunk
        chunk_size: Target characters per chunk (approximate, ~2 chars per token)
        overlap: Character overlap between chunks
    
    Returns:
        List of text chunks
    """
    # Convert token count to approximate character count (rough: 1 token ≈ 4 chars)
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4
    
    if not text.strip():
        return []
    
    chunks: List[str] = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + char_chunk_size, text_len)
        
        # Try to break at sentence or word boundary
        if end < text_len:
            # Look for sentence end
            sentence_end = text.rfind('. ', start, end)
            if sentence_end > start + (char_chunk_size // 2):
                end = sentence_end + 1
            else:
                # Look for word boundary
                space_pos = text.rfind(' ', start, end)
                if space_pos > start + (char_chunk_size // 2):
                    end = space_pos
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        
        # Move start position with overlap
        start = end - char_overlap if end - char_overlap > start else end
    
    return chunks


def extract_text_from_pdf_batch(pdf_path: Path, start_page: int, end_page: int) -> List[PageText]:
    """Extract text from a batch of PDF pages."""
    doc = fitz.open(pdf_path)
    pages: List[PageText] = []
    
    actual_end = min(end_page, len(doc))
    for page_num in range(start_page, actual_end):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text.strip():
            pages.append(PageText(page_num=page_num + 1, text=page_text))
    
    doc.close()
    return pages


async def index_documents() -> None:
    """Index therapy documents from data/therapy_docs/ into Supabase."""
    settings = get_settings()
    data_dir = PROJECT_ROOT / "data" / "therapy_docs"
    pdf_files = list(data_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("no_pdfs_found", path=str(data_dir))
        return

    logger.info("pdfs_found", count=len(pdf_files))

    embedding_service = await get_embedding_service()
    database = get_database()

    for pdf_path in pdf_files:
        logger.info("processing_pdf", file=str(pdf_path.name))
        
        # Get total page count
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        topic = infer_topic_from_filename(pdf_path.name)
        document_type = infer_document_type(pdf_path.name)
        logger.info(
            "pdf_metadata",
            file=pdf_path.name,
            topic=topic,
            document_type=document_type,
            pages=total_pages,
        )

        total_chunks = 0
        page_batch_size = 10  # Process 10 pages at a time
        embed_batch_size = 8  # Embed 8 chunks at a time
        
        # Process PDF in page batches
        for batch_start in range(0, total_pages, page_batch_size):
            batch_end = min(batch_start + page_batch_size, total_pages)
            
            logger.info(
                "processing_page_batch",
                file=pdf_path.name,
                pages=f"{batch_start + 1}-{batch_end}",
            )
            
            # Extract this batch of pages
            pages = extract_text_from_pdf_batch(pdf_path, batch_start, batch_end)
            
            if not pages:
                continue
            
            # Chunk each page and collect
            batch_chunks: List[DocumentChunk] = []
            
            for page in pages:
                page_chunks = chunk_text_by_characters(
                    page.text,
                    chunk_size=settings.CHUNK_SIZE,
                    overlap=settings.CHUNK_OVERLAP,
                )

                for chunk_text in page_chunks:
                    # Approximate token count for metadata
                    chunk_length = len(chunk_text) // 4  # Rough estimate
                    
                    batch_chunks.append(
                        DocumentChunk(
                            content=chunk_text,
                            metadata={
                                "source_file": pdf_path.name,
                                "chunk_index": total_chunks,
                                "page_number": page.page_num,
                                "topic": topic,
                                "document_type": document_type,
                                "chunk_length": chunk_length,
                            },
                        )
                    )
                    total_chunks += 1
            
            # Embed and insert in small batches
            for i in range(0, len(batch_chunks), embed_batch_size):
                embed_batch = batch_chunks[i:i + embed_batch_size]
                texts = [chunk.content for chunk in embed_batch]
                embeddings = await embedding_service.embed(texts)
                
                rows = [
                    {
                        "content": chunk.content,
                        "embedding": embedding,
                        "metadata": chunk.metadata,
                    }
                    for chunk, embedding in zip(embed_batch, embeddings)
                ]
                
                await database.insert_chunks(rows)
                logger.info(
                    "batch_inserted",
                    file=pdf_path.name,
                    batch_size=len(embed_batch),
                    total=total_chunks,
                )
            
            # Clear memory after each page batch
            pages.clear()
            batch_chunks.clear()
            gc.collect()
        
        logger.info("pdf_indexed", file=pdf_path.name, total_chunks=total_chunks)

    logger.info("indexing_complete", total_pdfs=len(pdf_files))


if __name__ == "__main__":
    asyncio.run(index_documents())
