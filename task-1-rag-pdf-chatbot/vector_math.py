import math
from typing import List, Dict, Any


def dot_product(vec_a: List[float], vec_b: List[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimensions must match ({len(vec_a)} != {len(vec_b)})")
    return sum(a * b for a, b in zip(vec_a, vec_b))


def vector_magnitude(vec: List[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def normalize_vector(vec: List[float]) -> List[float]:
    norm = vector_magnitude(vec)
    if norm == 0.0:
        return [0.0] * len(vec)
    return [x / norm for x in vec]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    mag_a = vector_magnitude(vec_a)
    mag_b = vector_magnitude(vec_b)
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot_product(vec_a, vec_b) / (mag_a * mag_b)


def cosine_distance(vec_a: List[float], vec_b: List[float]) -> float:
    return 1.0 - cosine_similarity(vec_a, vec_b)


def euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError("Vector dimensions must match")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)))


def compare_search_metrics(query_vec: List[float], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for cand in candidates:
        vec = cand["vector"]
        cos_sim = cosine_similarity(query_vec, vec)
        cos_dist = cosine_distance(query_vec, vec)
        euc_dist = euclidean_distance(query_vec, vec)
        
        norm_q = normalize_vector(query_vec)
        norm_c = normalize_vector(vec)
        norm_euc_dist = euclidean_distance(norm_q, norm_c)

        results.append({
            "text": cand.get("text", "Unknown"),
            "raw_vector": vec,
            "cosine_similarity": round(cos_sim, 4),
            "cosine_distance": round(cos_dist, 4),
            "euclidean_distance": round(euc_dist, 4),
            "normalized_euclidean_distance": round(norm_euc_dist, 4)
        })
    
    results.sort(key=lambda x: x["cosine_similarity"], reverse=True)
    return results


if __name__ == "__main__":
    query = [0.8, 0.6, 0.0]

    candidates = [
        {
            "text": "Machine learning healthcare applications",
            "vector": [0.75, 0.65, 0.1]
        },
        {
            "text": "AI in hospital systems guide",
            "vector": [3.2, 2.4, 0.0]
        },
        {
            "text": "Cooking delicious pasta recipes",
            "vector": [0.0, 0.1, 0.9]
        }
    ]

    comparisons = compare_search_metrics(query, candidates)
    for idx, res in enumerate(comparisons, 1):
        print(f"[{idx}] {res['text']}: Cosine={res['cosine_similarity']}, Euclidean={res['euclidean_distance']}")
