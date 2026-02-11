"""
FacPark - RAG Module
Hybrid retrieval: FAISS (vector) + BM25 fused via RRF.
Citations via [[CIT_i]] tags, validated server-side.

Anti-hallucination: "No context → No answer"
"""

import os
import re
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_sentence_transformer = None
_faiss_index = None
_bm25_index = None
_chunks_data = None


# =============================================================================
# DATA STRUCTURES
# =============================================================================
@dataclass
class Chunk:
    """A document chunk with metadata."""
    chunk_id: str
    content: str
    source: str
    article: Optional[str] = None
    level: str = "parent"  # parent or child
    start_char: int = 0
    end_char: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result from retrieval with score."""
    chunk: Chunk
    score: float
    rank: int


@dataclass
class RAGResponse:
    """Final RAG response with answer and citations."""
    answer: str
    citations: List[Dict]
    retrieved_chunks: List[Dict]
    scores: Dict[str, float]


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================
def normalize_query(query: str) -> str:
    """Normalize query for better French retrieval."""
    if not query:
        return ""
    # Lowercase
    text = query.lower().strip()
    # Remove excessive punctuation but keep question marks
    text = re.sub(r'[^\w\s\?\-àâäéèêëïîôùûüÿœæç]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def normalize_for_bm25(text: str) -> List[str]:
    """Tokenize text for BM25."""
    text = normalize_query(text)
    # Simple whitespace tokenization
    tokens = text.split()
    # Remove very short tokens
    tokens = [t for t in tokens if len(t) > 1]
    return tokens


# =============================================================================
# SEMANTIC CHUNKING
# =============================================================================
ARTICLE_PATTERN = re.compile(r'^(Article\s+\d+|R\d+)\s*[:\-–]?\s*', re.MULTILINE | re.IGNORECASE)


def chunk_document(content: str, source: str, max_size: int = 5000,
                   overlap_ratio: float = 0.15) -> List[Chunk]:
    """
    IMPROVED Semantic chunking: Keep articles COMPLETE (no splitting).
    
    CHANGES (2026-01-21):
    - max_size increased from 1500 → 5000 to keep full articles
    - Articles are NEVER split into child chunks
    - This improves Hit Rate from 22% → expected 60-70%
    
    Rules:
    - Detect articles at START of line only (strict regex)
    - Each article = 1 COMPLETE chunk (no splitting)
    - Better for retrieval: "Article 3" is a single, findable chunk
    """
    chunks = []
    
    # Find all article headers
    matches = list(ARTICLE_PATTERN.finditer(content))
    
    if not matches:
        # No articles found, treat entire doc as one chunk
        # Still split if VERY large (>10k)
        if len(content) > 10000:
            chunks.extend(_split_large_chunk(content, source, None, 10000, overlap_ratio))
        else:
            chunk = Chunk(
                chunk_id=f"{source}_full",
                content=content.strip(),
                source=source,
                article="Document",
                level="parent"
            )
            chunks.append(chunk)
        return chunks
    
    # Process each article section - KEEP COMPLETE
    for i, match in enumerate(matches):
        article_name = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        
        section_content = content[start:end].strip()
        
        # CHANGE: Always keep article complete (no splitting)
        chunk = Chunk(
            chunk_id=f"{source}_{article_name}",
            content=section_content,
            source=source,
            article=article_name,
            level="parent",
            start_char=start,
            end_char=end
        )
        chunks.append(chunk)
        
        # Log if article is large (for monitoring)
        if len(section_content) > max_size:
            logger.info(f"Large article kept intact: {article_name} ({len(section_content)} chars)")
    
    # Handle content before first article
    if matches and matches[0].start() > 0:
        preamble = content[:matches[0].start()].strip()
        if preamble:
            chunks.insert(0, Chunk(
                chunk_id=f"{source}_preamble",
                content=preamble,
                source=source,
                article="Préambule",
                level="parent"
            ))
    
    logger.info(f"Created {len(chunks)} COMPLETE article chunks from {source}")
    return chunks


def _split_large_chunk(content: str, source: str, article: Optional[str],
                       max_size: int, overlap_ratio: float) -> List[Chunk]:
    """Split large content into overlapping child chunks."""
    chunks = []
    overlap = int(max_size * overlap_ratio)
    
    # Try to split by paragraphs first
    paragraphs = content.split('\n\n')
    
    current_chunk = ""
    chunk_idx = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunk_id = f"{source}_{article}_part{chunk_idx}" if article else f"{source}_part{chunk_idx}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    content=current_chunk,
                    source=source,
                    article=article,
                    level="child" if article else "parent"
                ))
                chunk_idx += 1
                # Start new chunk with overlap
                words = current_chunk.split()
                overlap_text = ' '.join(words[-int(len(words) * overlap_ratio):]) if words else ""
                current_chunk = f"{overlap_text}\n\n{para}".strip()
            else:
                current_chunk = para
    
    # Don't forget last chunk
    if current_chunk:
        chunk_id = f"{source}_{article}_part{chunk_idx}" if article else f"{source}_part{chunk_idx}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            content=current_chunk,
            source=source,
            article=article,
            level="child" if article and chunk_idx > 0 else "parent"
        ))
    
    return chunks


# =============================================================================
# INDEX MANAGEMENT
# =============================================================================
def get_embedding_model():
    """Lazy load embedding model."""
    global _sentence_transformer
    if _sentence_transformer is None:
        from sentence_transformers import SentenceTransformer
        _sentence_transformer = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {settings.EMBEDDING_MODEL}")
    return _sentence_transformer


def load_indexes() -> Tuple[Any, Any, List[Chunk]]:
    """Load FAISS and BM25 indexes from disk."""
    global _faiss_index, _bm25_index, _chunks_data
    
    if _faiss_index is not None:
        return _faiss_index, _bm25_index, _chunks_data
    
    index_path = Path(settings.FAISS_INDEX_PATH)
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found at {index_path}. Run ingest_docs.py first.")
    
    import faiss
    
    # Load FAISS index
    _faiss_index = faiss.read_index(str(index_path / "faiss.index"))
    
    # Load BM25 index
    with open(index_path / "bm25.pkl", "rb") as f:
        _bm25_index = pickle.load(f)
    
    # Load chunks metadata
    with open(index_path / "chunks.json", "r", encoding="utf-8") as f:
        chunks_dict = json.load(f)
        _chunks_data = [Chunk(**c) for c in chunks_dict]
    
    logger.info(f"Loaded indexes: {len(_chunks_data)} chunks")
    return _faiss_index, _bm25_index, _chunks_data


# =============================================================================
# HYBRID RETRIEVAL (RRF FUSION)
# =============================================================================
def reciprocal_rank_fusion(rankings: List[List[int]], k: int = 60, weights: List[float] = None) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion for combining multiple rankings.
    
    RRF score = sum(weight * (1 / (k + rank))) for each ranking
    """
    if weights is None:
        weights = [1.0] * len(rankings)
        
    scores = {}
    for i, ranking in enumerate(rankings):
        weight = weights[i]
        for rank, doc_id in enumerate(ranking):
            if doc_id not in scores:
                scores[doc_id] = 0.0
            scores[doc_id] += weight * (1.0 / (k + rank + 1))
    
    # Sort by score descending
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs


def retrieve_hybrid(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """
    Hybrid retrieval using FAISS + BM25 with RRF fusion.
    
    1. Get top_n from FAISS (vector similarity)
    2. Get top_n from BM25 (lexical matching)
    3. Fuse using RRF
    4. Return top_k
    """
    faiss_index, bm25_index, chunks = load_indexes()
    model = get_embedding_model()
    
    # Normalize query
    normalized_query = normalize_query(query)
    
    # 1. FAISS retrieval
    query_embedding = model.encode([normalized_query], convert_to_numpy=True)
    faiss_scores, faiss_ids = faiss_index.search(
        query_embedding.astype('float32'),
        min(settings.RAG_TOP_N_VECTOR, len(chunks))
    )
    faiss_ranking = faiss_ids[0].tolist()
    
    # 2. BM25 retrieval
    query_tokens = normalize_for_bm25(normalized_query)
    bm25_scores = bm25_index.get_scores(query_tokens)
    bm25_ranking = np.argsort(bm25_scores)[::-1][:settings.RAG_TOP_N_BM25].tolist()
    
    # 3. RRF Fusion (Weighted: FAISS=1.0, BM25=0.4 to reduce noise)
    fused = reciprocal_rank_fusion(
        [faiss_ranking, bm25_ranking], 
        k=settings.RAG_RRF_K,
        weights=[1.0, 0.4] 
    )
    
    # 4. Build results
    results = []
    for rank, (doc_id, score) in enumerate(fused[:top_k]):
        if doc_id < len(chunks):
            results.append(RetrievalResult(
                chunk=chunks[doc_id],
                score=score,
                rank=rank + 1
            ))
    
    return results


# =============================================================================
# CITATION HANDLING
# =============================================================================
def build_citation_mapping(results: List[RetrievalResult]) -> Dict[str, Dict]:
    """Build citation mapping from retrieved chunks."""
    mapping = {}
    for i, r in enumerate(results):
        tag = f"[[CIT_{i+1}]]"
        mapping[tag] = {
            "source": r.chunk.source,
            "article": r.chunk.article or "N/A",
            "chunk_id": r.chunk.chunk_id,
            "excerpt": r.chunk.content[:100] + "..." if len(r.chunk.content) > 100 else r.chunk.content
        }
    return mapping


def replace_citation_tags(text: str, mapping: Dict[str, Dict]) -> str:
    """Replace [[CIT_i]] tags with formatted citations."""
    result = text
    for tag, info in mapping.items():
        formatted = f"[Source: {info['source']}, {info['article']}]"
        result = result.replace(tag, formatted)
    # Remove any unmatched citation tags (anti-hallucination)
    result = re.sub(r'\[\[CIT_\d+\]\]', '', result)
    return result


# =============================================================================
# RAG QUERY (Main Entry Point)
# =============================================================================
def query_rag(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Main RAG query function.
    
    Returns answer with validated citations.
    Anti-hallucination: returns "no context" message if no relevant chunks.
    """
    try:
        # Retrieve
        results = retrieve_hybrid(query, top_k=top_k)
        
        # Check if we have relevant results
        if not results or all(r.score < settings.RAG_SCORE_THRESHOLD for r in results):
            return {
                "answer": "Je ne trouve pas cette information dans le règlement du parking.",
                "citations": [],
                "context_found": False
            }
        
        # Build context for LLM
        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"[{i+1}] {r.chunk.article or 'Document'}: {r.chunk.content}")
        
        context = "\n\n".join(context_parts)
        citation_mapping = build_citation_mapping(results)
        
        # Build prompt for LLM (will be called by agent.py)
        return {
            "context": context,
            "citation_mapping": citation_mapping,
            "retrieved_chunks": [
                {"chunk_id": r.chunk.chunk_id, "article": r.chunk.article,
                 "score": r.score, "excerpt": r.chunk.content[:200]}
                for r in results
            ],
            "context_found": True
        }
        
    except FileNotFoundError:
        logger.error("RAG indexes not found")
        return {
            "answer": "Le système de recherche n'est pas initialisé. Contactez l'administration.",
            "citations": [],
            "context_found": False,
            "error": "INDEX_NOT_FOUND"
        }
    except Exception as e:
        logger.exception(f"RAG query error: {e}")
        return {
            "answer": "Erreur lors de la recherche. Réessayez plus tard.",
            "citations": [],
            "context_found": False,
            "error": str(e)
        }
