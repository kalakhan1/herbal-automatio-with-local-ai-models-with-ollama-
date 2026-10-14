"""Duplicate detection using TF-IDF cosine similarity."""
import logging
import re
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import Config

log = logging.getLogger(__name__)

def _clean(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def check_duplicates(items: List[Dict], text_key: str = "product_content") -> List[Dict]:
    """
    Given list of products, compute pairwise similarity.
    Returns list of {id, max_similarity, most_similar_to}.
    """
    if len(items) < 2:
        return [{"id": it["id"], "max_similarity": 0.0, "most_similar_to": None}
                for it in items]

    texts = [_clean(it.get(text_key, "")) for it in items]

    # Filter empty
    valid_idx = [i for i, t in enumerate(texts) if len(t) > 50]
    if len(valid_idx) < 2:
        return [{"id": items[i]["id"], "max_similarity": 0.0,
                 "most_similar_to": None} for i in range(len(items))]

    try:
        vec = TfidfVectorizer(max_features=5000, stop_words="english")
        matrix = vec.fit_transform([texts[i] for i in valid_idx])
        sim_matrix = cosine_similarity(matrix)
    except Exception as e:
        log.warning(f"TF-IDF failed: {e}")
        return [{"id": items[i]["id"], "max_similarity": 0.0,
                 "most_similar_to": None} for i in range(len(items))]

    results = []
    for idx_in_valid, global_idx in enumerate(valid_idx):
        sims = sim_matrix[idx_in_valid].copy()
        sims[idx_in_valid] = 0  # ignore self
        if len(sims) == 0:
            continue
        max_sim = float(sims.max())
        max_arg = int(sims.argmax())
        similar_to = items[valid_idx[max_arg]]["id"]
        results.append({
            "id": items[global_idx]["id"],
            "max_similarity": round(max_sim, 3),
            "most_similar_to": similar_to
        })

    # Add zeros for empty ones
    result_ids = {r["id"] for r in results}
    for it in items:
        if it["id"] not in result_ids:
            results.append({"id": it["id"], "max_similarity": 0.0,
                            "most_similar_to": None})
    return results