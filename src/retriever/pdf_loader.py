"""
PDF Loader for Medical Literature

Ingests PDF documents from data/pdfs/ directory and prepares them
for the retrieval system.

For Mock Version: Simple text extraction and storage
For Full CLaRa: Document compression using CLaRa Stage 1/2 models
"""

import os
from typing import List, Dict
from pathlib import Path
from loguru import logger

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("⚠️ pdfplumber not installed. PDF loading disabled.")


class PDFLoader:
    """
    PDF Document Loader
    
    Loads medical/dietetics PDFs and extracts text for retrieval.
    """
    
    def __init__(self, pdf_directory: str = "./data/pdfs"):
        """
        Initialize PDF loader
        
        Args:
            pdf_directory: Directory containing PDF files
        """
        self.pdf_directory = Path(pdf_directory)
        self.documents = []
        
        logger.info(f"📁 PDF Loader initialized for directory: {self.pdf_directory}")
    
    def load_all_pdfs(self) -> List[Dict]:
        """
        Load all PDFs from the configured directory
        
        Returns:
            List of document dictionaries with text and metadata
        """
        if not PDF_SUPPORT:
            logger.error("❌ Cannot load PDFs - pdfplumber not installed")
            return []
        
        if not self.pdf_directory.exists():
            logger.warning(f"⚠️ PDF directory does not exist: {self.pdf_directory}")
            logger.info("Creating directory...")
            self.pdf_directory.mkdir(parents=True, exist_ok=True)
            return []
        
        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"⚠️ No PDF files found in {self.pdf_directory}")
            return []
        
        logger.info(f"📚 Found {len(pdf_files)} PDF file(s)")
        
        for pdf_path in pdf_files:
            try:
                doc = self.load_pdf(pdf_path)
                if doc:
                    self.documents.append(doc)
            except Exception as e:
                logger.error(f"❌ Error loading {pdf_path.name}: {e}")
        
        logger.success(f"✅ Loaded {len(self.documents)} PDF document(s)")
        return self.documents
    
    def load_pdf(self, pdf_path: Path) -> Dict:
        """
        Load a single PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Document dictionary with text and metadata
        """
        if not PDF_SUPPORT:
            return None
        
        logger.info(f"📖 Loading: {pdf_path.name}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_chunks = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_chunks.append(text)
                
                full_text = "\n\n".join(text_chunks)
                
                document = {
                    "title": pdf_path.stem,
                    "filename": pdf_path.name,
                    "path": str(pdf_path),
                    "text": full_text,
                    "page_count": len(pdf.pages),
                    "metadata": {
                        "source": "pdf",
                        "file_size": pdf_path.stat().st_size
                    }
                }
                
                logger.success(
                    f"✅ Extracted {len(pdf.pages)} page(s) from {pdf_path.name}"
                )
                
                return document
                
        except Exception as e:
            logger.error(f"❌ Error extracting text from {pdf_path.name}: {e}")
            return None
    
    def chunk_documents(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict]:
        """
        Split documents into smaller chunks for retrieval
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of chunked documents
        """
        chunked_docs = []
        
        for doc in self.documents:
            text = doc["text"]
            chunks = self._split_text(text, chunk_size, chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                chunked_doc = {
                    "title": f"{doc['title']} (Part {i+1}/{len(chunks)})",
                    "text": chunk,
                    "source_document": doc["filename"],
                    "chunk_index": i,
                    "metadata": doc["metadata"]
                }
                chunked_docs.append(chunked_doc)
        
        logger.info(
            f"📄 Chunked {len(self.documents)} document(s) into "
            f"{len(chunked_docs)} chunk(s)"
        )
        
        return chunked_docs
    
    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start += chunk_size - chunk_overlap
        
        return chunks
    
    def get_document_stats(self) -> Dict:
        """
        Get statistics about loaded documents
        
        Returns:
            Dictionary with document statistics
        """
        if not self.documents:
            return {"count": 0}
        
        total_pages = sum(doc.get("page_count", 0) for doc in self.documents)
        total_chars = sum(len(doc["text"]) for doc in self.documents)
        
        return {
            "count": len(self.documents),
            "total_pages": total_pages,
            "total_characters": total_chars,
            "average_pages_per_doc": total_pages / len(self.documents) if self.documents else 0
        }


# Utility function for easy importing
def load_medical_literature(pdf_dir: str = "./data/pdfs") -> List[Dict]:
    """
    Convenience function to load all medical PDFs
    
    Args:
        pdf_dir: Directory containing PDFs
    
    Returns:
        List of loaded documents
    """
    loader = PDFLoader(pdf_dir)
    documents = loader.load_all_pdfs()
    
    if documents:
        stats = loader.get_document_stats()
        logger.info(f"📊 Loaded {stats['count']} documents, {stats['total_pages']} pages")
    
    return documents


if __name__ == "__main__":
    # Test PDF loading
    logger.info("🧪 Testing PDF Loader...")
    
    docs = load_medical_literature()
    
    if docs:
        logger.success(f"✅ Test successful! Loaded {len(docs)} document(s)")
        for doc in docs:
            logger.info(f"  - {doc['title']}: {doc['page_count']} pages")
    else:
        logger.warning("⚠️ No documents loaded (this is expected if data/pdfs/ is empty)")
