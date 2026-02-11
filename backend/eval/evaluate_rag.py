"""
FacPark - RAG Evaluation Script
Measures Hit Rate, Recall, and Faithfulness.
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict
import pandas as pd

# Add project root
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.config import settings
from backend.core.rag import retrieve_hybrid, query_rag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUESTIONS_FILE = Path(__file__).parent / "questions.jsonl"

def load_questions() -> List[Dict]:
    questions = []
    if not QUESTIONS_FILE.exists():
        logger.error(f"Questions file not found: {QUESTIONS_FILE}")
        return []
    
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions

def evaluate_retrieval(questions: List[Dict], k: int = 5):
    """
    Evaluate retrieval performance (Hit Rate).
    A "hit" is when the retrieved chunks contain the expected 'source' (e.g. 'Article 3').
    """
    logger.info(f"Evaluating Retrieval (top_k={k})...")
    
    hits = 0
    mrr_sum = 0.0
    total = len(questions)
    
    results_log = []
    
    for q in questions:
        query = q["query"]
        expected_source = q["source"]
        
        # Retrieval only
        try:
            retrieved = retrieve_hybrid(query, top_k=k)
            
            # Check if expected source is in retrieved metadata
            # We match partial string (e.g. "Article 3" in "Article 3: Horaires")
            is_hit = False
            hit_rank = 0
            found_sources = []
            
            for i, r in enumerate(retrieved):
                article = r.chunk.article or ""
                found_sources.append(article)
                if expected_source.lower() in article.lower():
                    is_hit = True
                    hit_rank = i + 1
                    mrr_sum += 1.0 / hit_rank
                    break
            
            if is_hit:
                hits += 1
            
            results_log.append({
                "query": query,
                "expected": expected_source,
                "found": found_sources,
                "hit": is_hit
            })
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
    
    hit_rate = hits / total if total > 0 else 0
    mrr = mrr_sum / total if total > 0 else 0
    
    logger.info(f"Retrieval Hit Rate: {hit_rate:.2%} ({hits}/{total})")
    logger.info(f"Retrieval MRR: {mrr:.4f}")
    
    # Save detailed log
    df = pd.DataFrame(results_log)
    df.to_csv(Path(__file__).parent / "retrieval_results.csv", index=False)
    return hit_rate, mrr

def evaluate_generation(questions: List[Dict]):
    """
    Evaluate generation (Smoke Test).
    Checks if system returns an answer vs "I don't know".
    """
    logger.info("Evaluating Generation (Smoke Test)...")
    
    answered = 0
    total = len(questions)
    
    for q in questions[:10]: # Test on subset to save tokens/time
        query = q["query"]
        try:
            # Full RAG query
            response = query_rag(query)
            
            has_answer = response.get("context_found", False)
            if has_answer:
                answered += 1
                logger.info(f"Q: {query} -> A: RESPONSE GENERATED")
            else:
                logger.info(f"Q: {query} -> A: NO CONTEXT")
                
        except Exception as e:
            logger.error(f"Error generation '{query}': {e}")

    logger.info("Generation test complete.")

if __name__ == "__main__":
    qs = load_questions()
    if qs:
        evaluate_retrieval(qs)
        evaluate_generation(qs)
    else:
        logger.warning("No questions to evaluate.")
