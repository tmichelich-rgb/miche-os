"""
RAG Pipeline: PDF extraction, semantic chunking, TF-IDF indexing.
Fuente de verdad: 3 libros de Miguel Miranda.
"""
import os
import re
import json
import pickle
import fitz  # PyMuPDF
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional

BOOKS = {
    "programacion_lineal": {
        "filename": "PROGRAMACION LINEAL Y SU ENTORNO - MIGUEL MIRANDA.pdf",
        "short": "LP",
        "author": "Miguel Miranda",
    },
    "stocks": {
        "filename": "SISTEMAS DE OPTIMIZACION DE STOCKS - MIGUEL MIRANDA.pdf",
        "short": "STOCK",
        "author": "Miguel Miranda",
    },
    "teoria_colas": {
        "filename": "TEORIA DE COLAS - MIGUEL MIRANDA.pdf",
        "short": "QUEUE",
        "author": "Miguel Miranda",
    },
}

# Keywords for chunk type detection
DEFINITION_MARKERS = [
    "se define", "se denomina", "llamaremos", "definición", "definimos",
    "entendemos por", "se entiende por", "concepto de", "se llama",
]
FORMULA_MARKERS = [
    "=", "√", "∑", "≤", "≥", "λ", "μ", "ρ", "∞",
    "fórmula", "expresión", "ecuación", "cálculo",
]
WARNING_MARKERS = [
    "advertencia", "cuidado", "no debe", "no se puede", "condición necesaria",
    "supuesto", "limitación", "restricción", "sólo si", "solo si", "requisito",
    "no aplica", "ρ < 1", "ρ<1",
]
EXAMPLE_MARKERS = [
    "ejemplo", "aplicación", "ejercicio", "caso práctico", "resolución",
    "planteo", "solución",
]
PROCEDURE_MARKERS = [
    "paso 1", "paso 2", "procedimiento", "algoritmo", "método",
    "iteración", "etapa", "se procede",
]


class Chunk:
    """A semantic chunk from one of the source PDFs."""
    def __init__(self, text: str, book: str, chapter: int, section: str,
                 chunk_type: str, page_start: int, page_end: int,
                 model_id: str = "", keywords: List[str] = None):
        self.text = text
        self.book = book
        self.chapter = chapter
        self.section = section
        self.chunk_type = chunk_type
        self.page_start = page_start
        self.page_end = page_end
        self.model_id = model_id
        self.keywords = keywords or []
        self.has_formula = any(m in text for m in ["=", "√", "∑", "≤", "≥"])

    def to_dict(self):
        return {
            "text": self.text,
            "book": self.book,
            "chapter": self.chapter,
            "section": self.section,
            "chunk_type": self.chunk_type,
            "page_range": f"{self.page_start}-{self.page_end}",
            "model_id": self.model_id,
            "keywords": self.keywords,
            "has_formula": self.has_formula,
        }


def detect_chunk_type(text: str) -> str:
    """Classify chunk by content markers."""
    text_lower = text.lower()
    scores = {
        "example": sum(1 for m in EXAMPLE_MARKERS if m in text_lower),
        "definition": sum(1 for m in DEFINITION_MARKERS if m in text_lower),
        "formula": sum(1 for m in FORMULA_MARKERS if m in text),
        "warning": sum(1 for m in WARNING_MARKERS if m in text_lower),
        "procedure": sum(1 for m in PROCEDURE_MARKERS if m in text_lower),
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "content"
    return best


def detect_model_id(text: str, book_key: str) -> str:
    """Detect specific model referenced in chunk."""
    text_lower = text.lower()

    if book_key == "programacion_lineal":
        if "simplex" in text_lower:
            return "simplex"
        if "dual" in text_lower:
            return "dual"
        if "sensibilidad" in text_lower or "rango" in text_lower:
            return "sensitivity"
        if "entero" in text_lower or "binari" in text_lower:
            return "integer"
        return "lp_general"

    elif book_key == "stocks":
        if "agotamiento" in text_lower or "faltante" in text_lower:
            return "eoq_shortage"
        if "gradual" in text_lower or "no instantáne" in text_lower:
            return "eoq_gradual"
        if "descuento" in text_lower:
            return "eoq_discount"
        if "protección" in text_lower or "seguridad" in text_lower:
            return "safety_stock"
        if any(w in text_lower for w in ["qo", "lote óptimo", "eoq", "cantidad óptima"]):
            return "eoq_basic"
        return "stock_general"

    elif book_key == "teoria_colas":
        # Check specific models
        if "impacien" in text_lower or "abandono" in text_lower:
            return "queue_impatience"
        if "red" in text_lower and "cola" in text_lower:
            return "queue_network"
        if "serie" in text_lower or "bloqueo" in text_lower:
            return "queue_series"
        if "prioridad" in text_lower:
            return "queue_priority"
        if "población finita" in text_lower:
            return "queue_finite_pop"
        # M/M/M/N
        if any(p in text_lower for p in ["p/p/m/n", "m/m/m/n", "varios canales", "múltiples servidores"]):
            if "capacidad" in text_lower or "finit" in text_lower:
                return "mmm_n"
            return "mmm"
        # M/M/1/N
        if any(p in text_lower for p in ["p/p/1/n", "m/m/1/n"]):
            return "mm1_n"
        # M/M/1
        if any(p in text_lower for p in ["p/p/1", "m/m/1", "un solo canal", "un servidor"]):
            return "mm1"
        return "queue_general"

    return "unknown"


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text page by page from PDF."""
    pages = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append({"page": i + 1, "text": text.strip()})
    doc.close()
    return pages


def detect_chapter(text: str, page_num: int) -> int:
    """Try to detect chapter number from text."""
    patterns = [
        r'[Cc]ap[ií]tulo\s+(\d+)',
        r'CAP[IÍ]TULO\s+(\d+)',
        r'^(\d+)\.\s+[A-ZÁÉÍÓÚ]',
        r'TEMA\s+(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:500])
        if match:
            return int(match.group(1))
    return 0


def semantic_chunk(pages: List[Dict], book_key: str,
                   min_chunk_size: int = 200, max_chunk_size: int = 1500) -> List[Chunk]:
    """
    Chunk pages semantically based on content structure.
    Uses paragraph boundaries and content type shifts as split points.
    """
    chunks = []
    current_text = ""
    current_chapter = 0
    current_page_start = 1

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]

        # Detect chapter changes
        ch = detect_chapter(text, page_num)
        if ch > 0:
            current_chapter = ch

        # Split page into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        for para in paragraphs:
            para = para.strip()
            if len(para) < 30:
                continue

            # Check if adding this paragraph would exceed max size
            if len(current_text) + len(para) > max_chunk_size and len(current_text) >= min_chunk_size:
                # Save current chunk
                chunk = Chunk(
                    text=current_text.strip(),
                    book=book_key,
                    chapter=current_chapter,
                    section=f"{current_chapter}.0",
                    chunk_type=detect_chunk_type(current_text),
                    page_start=current_page_start,
                    page_end=page_num,
                    model_id=detect_model_id(current_text, book_key),
                )
                chunks.append(chunk)
                current_text = ""
                current_page_start = page_num

            current_text += " " + para

    # Don't forget last chunk
    if len(current_text.strip()) >= min_chunk_size:
        chunk = Chunk(
            text=current_text.strip(),
            book=book_key,
            chapter=current_chapter,
            section=f"{current_chapter}.0",
            chunk_type=detect_chunk_type(current_text),
            page_start=current_page_start,
            page_end=pages[-1]["page"] if pages else 0,
            model_id=detect_model_id(current_text, book_key),
        )
        chunks.append(chunk)

    return chunks


class RAGIndex:
    """TF-IDF based RAG index for the Miranda books."""

    def __init__(self):
        self.chunks: List[Chunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.is_indexed = False

    def index_pdfs(self, pdf_dir: str):
        """Index all 3 PDFs from directory."""
        all_chunks = []

        for book_key, book_info in BOOKS.items():
            pdf_path = os.path.join(pdf_dir, book_info["filename"])
            if not os.path.exists(pdf_path):
                print(f"WARNING: {pdf_path} not found, skipping.")
                continue

            print(f"Extracting: {book_info['filename']}...")
            pages = extract_text_from_pdf(pdf_path)
            print(f"  → {len(pages)} pages extracted")

            chunks = semantic_chunk(pages, book_key)
            print(f"  → {len(chunks)} chunks created")

            # Print chunk type distribution
            types = {}
            for c in chunks:
                types[c.chunk_type] = types.get(c.chunk_type, 0) + 1
            print(f"  → Types: {types}")

            all_chunks.extend(chunks)

        self.chunks = all_chunks
        print(f"\nTotal chunks: {len(self.chunks)}")

        # Build TF-IDF index
        print("Building TF-IDF index...")
        texts = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words=None,  # Keep Spanish stopwords for now
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self.is_indexed = True
        print("Index ready!")

    def search(self, query: str, top_k: int = 5,
               book_filter: str = None,
               chunk_type_filter: str = None,
               model_id_filter: str = None) -> List[Dict]:
        """
        Search the index with optional filters.
        Returns list of {chunk, score, citation}.
        """
        if not self.is_indexed:
            return []

        # Transform query
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Apply filters
        for i, chunk in enumerate(self.chunks):
            if book_filter and chunk.book != book_filter:
                scores[i] = 0.0
            if chunk_type_filter and chunk.chunk_type != chunk_type_filter:
                scores[i] *= 0.5  # Penalize but don't exclude
            if model_id_filter and chunk.model_id != model_id_filter:
                scores[i] *= 0.7

        # Get top-k
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] < 0.01:
                continue
            chunk = self.chunks[idx]
            results.append({
                "text": chunk.text[:800],  # Truncate for response
                "score": float(scores[idx]),
                "citation": {
                    "book": chunk.book,
                    "chapter": chunk.chapter,
                    "section": chunk.section,
                    "page_range": f"{chunk.page_start}-{chunk.page_end}",
                    "chunk_type": chunk.chunk_type,
                    "model_id": chunk.model_id,
                },
            })

        return results

    def save(self, path: str):
        """Save index to disk."""
        data = {
            "chunks": [c.to_dict() for c in self.chunks],
            "vectorizer": self.vectorizer,
            "tfidf_matrix": self.tfidf_matrix,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"Index saved to {path}")

    def load(self, path: str):
        """Load index from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        # Reconstruct chunks
        self.chunks = []
        for cd in data["chunks"]:
            chunk = Chunk(
                text=cd["text"],
                book=cd["book"],
                chapter=cd["chapter"],
                section=cd["section"],
                chunk_type=cd["chunk_type"],
                page_start=int(cd["page_range"].split("-")[0]),
                page_end=int(cd["page_range"].split("-")[1]),
                model_id=cd.get("model_id", ""),
                keywords=cd.get("keywords", []),
            )
            self.chunks.append(chunk)
        self.vectorizer = data["vectorizer"]
        self.tfidf_matrix = data["tfidf_matrix"]
        self.is_indexed = True
        print(f"Index loaded: {len(self.chunks)} chunks")


# Singleton
_index = RAGIndex()


def get_index() -> RAGIndex:
    return _index


if __name__ == "__main__":
    import sys
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "/sessions/nice-eloquent-cori/mnt/Investigacion Operativa"
    idx = get_index()
    idx.index_pdfs(pdf_dir)
    idx.save(os.path.join(pdf_dir, ".rag_index.pkl"))
