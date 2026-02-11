"""
FacPark - Documentation Ingestion Script
Indexes documents into FAISS and BM25 for RAG.
Run this script to initialize/update the retrieval system.
"""

import sys
import os
import json
import pickle
import logging
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.config import settings
from backend.core.rag import chunk_document, get_embedding_model

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def ingest_docs():
    """Main ingestion function."""
    
    # 1. Setup paths
    docs_dir = Path(settings.DOCS_DIR)
    index_path = Path(settings.FAISS_INDEX_PATH)
    index_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Scanning documents in {docs_dir}")
    
    documents = []
    for doc_file in docs_dir.glob("*.txt"):
        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append({"source": doc_file.name, "content": content})
    
    if not documents:
        logger.warning(f"No .txt documents found in {docs_dir}")
        return

    # 2. Chunking
    logger.info("Chunking documents...")
    all_chunks = []
    
    # MANUAL KEYWORDS MAPPING (Enrichment)
    KEYWORDS_MAPPING = {
        "Article 5": "moto, scooter, deux-roues, mobylette, bicyclette, véhicule, autorisé, permis",
        "Article 4": "place de parking, stationnement, garer, emplacement, zone",
        "Article 2": "types abonnement, durée, validité",
        "Article 1": "horaire, ouverture, fermeture, dimanche, nuit, accès",
        "Article 9": "panne, réparation, garage, remplacement, voiture de prêt",
        "Article 10": "invité, étranger, extérieur, amis, famille, visiteur",
        "Article 11": "caméra, surveillance, surveillé, sécurité, vidéo, vol",
        "Article 14": "sanction, punition, amende, risque, prison, police, exclusion, renvoi",
        "Article 16": "badge, inscription, comment faire, procédure, papiers, dossier, carte",
        "Article 19": "refus, erreur, problème, barrière, ne s'ouvre pas, bloqué, rouge",
        "Annexe A": "prix, tarif, coût, combien, argent, payer, facture"
    }
    
    for doc in documents:
        chunks = chunk_document(
            content=doc["content"],
            source=doc["source"],
            max_size=settings.CHUNK_MAX_SIZE,
            overlap_ratio=settings.CHUNK_OVERLAP_RATIO
        )
        
        # Enrich chunks with keywords
        for chunk in chunks:
            if chunk.article in KEYWORDS_MAPPING:
                keywords = KEYWORDS_MAPPING[chunk.article]
                logger.info(f"Enriching {chunk.chunk_id} with keywords: {keywords}")
                # Append to content so it's indexed by both FAISS and BM25
                chunk.content += f"\n\n[Mots-clés associés: {keywords}]"
                chunk.metadata["keywords"] = keywords
                
        all_chunks.extend(chunks)
    
    logger.info(f"Generated {len(all_chunks)} chunks.")

    # 3. Vector Embeddings (FAISS)
    logger.info(f"Embedding chunks using {settings.EMBEDDING_MODEL}...")
    model = get_embedding_model()
    
    chunk_texts = [c.content for c in all_chunks]
    embeddings = model.encode(chunk_texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype('float32') # FAISS requires float32
    
    import faiss
    dimension = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dimension) # Inner Product (cosine if normalized)
    # Validate normalization (SentenceTransformers usually outputs normalized vectors)
    faiss.normalize_L2(embeddings)
    faiss_index.add(embeddings)
    
    # Save FAISS index
    faiss.write_index(faiss_index, str(index_path / "faiss.index"))
    logger.info("FAISS index saved.")

    # 4. BM25 Index
    logger.info("Building BM25 index...")
    from rank_bm25 import BM25Okapi
    from backend.core.rag import normalize_for_bm25
    
    tokenized_corpus = [normalize_for_bm25(text) for text in chunk_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Save BM25 index
    with open(index_path / "bm25.pkl", "wb") as f:
        pickle.dump(bm25, f)
    logger.info("BM25 index saved.")

    # 5. Save Metadata
    logger.info("Saving chunk metadata...")
    chunks_data = [
        {
            "chunk_id": c.chunk_id,
            "content": c.content,
            "source": c.source,
            "article": c.article,
            "level": c.level,
            "metadata": c.metadata
        }
        for c in all_chunks
    ]
    with open(index_path / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)

    logger.info("Ingestion complete successfully!")


if __name__ == "__main__":
    ingest_docs()
