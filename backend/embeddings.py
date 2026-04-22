"""
embeddings.py

Establishes functions used in querying the ChromaDB database of wine description embeddings.
"""
import pandas as pd
import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer
import chromadb


### Global Variables and Configuration
CHROMA_DB_PATH     = "./wine_db"
COLLECTION_NAME    = "wines"
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"

_model: Optional[SentenceTransformer] = None
_collection: Optional[chromadb.Collection] = None
 

# Load Sentence tranformer once to reduce computation time
def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it across all requests."""
    global _model
    if _model is None:
        print(f"[embeddings] Loading model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model
 
# Load chromaDB collection once to reduce computation time
def get_collection() -> chromadb.Collection:
    """Connect to the ChromaDB collection once and reuse the handle."""
    global _collection
    if _collection is None:
        print(f"[embeddings] Connecting to ChromaDB at: {CHROMA_DB_PATH}")
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
        print(f"[embeddings] Collection loaded: {_collection.count():,} wines")
    return _collection
 


### Helper functions
def _price_filter(price_min : float, price_max: float) -> dict:
    return [
        {"price": {"$gte": max(price_min, 0.0)}},
        {"price": {"$lte": price_max}},
    ]

def _or_filter(field: str, values: list[str]) -> Optional[dict]:
    """
    Builds a $or filter for a single field across multiple allowed values.
    Returns None if values list is empty.
    """
    if not values:
        return None
 
    # Filter out blank strings before deciding how to wrap
    clean = [v for v in values if v and v.strip()]
 
    if not clean:
        return None
    if len(clean) == 1:
        return {field: {"$eq": clean[0]}}
 
    return {
        "$or": [
            {field: {"$eq": value}}
            for value in clean
        ]
    }

### Query Combining Logic

def build_filter(
        price_min : Optional[float] = None,
        price_max : Optional[float] = None,
        regions : Optional[dict] = None,
        countries : Optional[dict] = None,
        varietals : Optional[dict] = None,
) -> Optional[dict]:
    """
    Takes in all filters, and turns them into one ChromaDB where clause
    Returns None if no filters are chosen.
    """

    conditions: list[dict] = []
    if price_min is not None and price_max is not None:
        conditions.extend(_price_filter(price_min, price_max))
    elif price_max is not None:
        # Max price only — still exclude unknown-price wines
        conditions.append({"price": {"$lte": price_max}})
        conditions.append({"price": {"$gte": 0}})
    
    # Region
    if regions:
        region_f = _or_filter("region_1", regions)
        if region_f:
            conditions.append(region_f)
 
    # Country
    if countries:
        country_f = _or_filter("country", countries)
        if country_f:
            conditions.append(country_f)
 
    # Varietal
    if varietals:
        varietal_f = _or_filter("variety", varietals)
        if varietal_f:
            conditions.append(varietal_f)
 
    # If no conditions, return None, and do normal query based search
    if not conditions:
        return None     
    # No combining and needed if only 1 filter                  
    if len(conditions) == 1:
        return conditions[0]   
    # Otherwise, return the conditions seperated by and
    return {"$and": conditions} 
    
    

### Main embedding logic

def get_recommended_wines(
        query : str,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        regions: Optional[list[str]] = None,
        countries: Optional[list[str]] = None,
        varietals: Optional[list[str]] = None,
        num_results : Optional[str] = 10,
        mmr : bool = True,
        mmr_lambda: float = 0.7,
        mmr_fetch_k: int = 50, 
) -> list[dict]:
    """
    takes in an initial query from the user along with price, region, country, and varietal
    filters, and returns a dictionary object of the top 10 wines in the ChromaDB database
    by cosine similarity with the description of that wine.
    """

    model = get_model()
    collection = get_collection()

    query_embedding = model.encode([query]).tolist()
 
    filter = build_filter(price_min, price_max, regions, countries, varietals)

    kwargs = {
        "query_embeddings": query_embedding,
        "n_results": mmr_fetch_k if mmr else num_results,
        "include": ["documents", "metadatas", "distances", "embeddings"],
        }
    
    if filter:
        kwargs["where"] = filter


    try:
        results = collection.query(**kwargs)
    except Exception as e:
        print(f"[embeddings] ChromaDB query failed: {e}")
        return []
    
    wines = []
    
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        wines.append({
            "title":       meta.get("title", ""),
            "winery":      meta.get("winery", ""),
            "variety":     meta.get("variety", ""),
            "country":     meta.get("country", ""),
            "province":    meta.get("province", ""),
            "region_1":    meta.get("region_1", ""),
            "points":      meta.get("points", 0),
            "price":       meta.get("price", -1.0),
            "description": doc,
            # Convert cosine distance → similarity score (distance of 0 = perfect match)
            "similarity":  round(1 - dist, 4),
        })

    if mmr and results.get("embeddings"):
        candidate_embeddings = results["embeddings"][0]
        candidates = wines  # the already-unpacked list
        return mmr_select(query_embedding[0], candidate_embeddings, candidates, num_results, mmr_lambda)
 
    return wines

import numpy as np

def mmr_select(
    query_embedding: list[float],
    candidate_embeddings: list[list[float]],
    candidates: list[dict],
    k: int = 10,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance selection over a candidate set.
    
    query_embedding:      the embedded user query (1D)
    candidate_embeddings: embeddings of all candidates returned by ChromaDB
    candidates:           the unpacked wine dicts matching candidate_embeddings
    k:                    how many wines to return
    lambda_param:         0=max diversity, 1=max similarity, 0.7 is a good default
    """
    query_vec = np.array(query_embedding)
    cand_vecs = np.array(candidate_embeddings)

    # Cosine similarity between query and all candidates
    query_sims = cand_vecs @ query_vec / (
        np.linalg.norm(cand_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-10
    )

    selected_indices = []
    remaining = list(range(len(candidates)))

    for _ in range(min(k, len(candidates))):
        if not selected_indices:
            # First pick — pure similarity to query
            best = max(remaining, key=lambda i: query_sims[i])
        else:
            # Subsequent picks — balance similarity vs redundancy
            selected_vecs = cand_vecs[selected_indices]
            scores = []
            for i in remaining:
                relevance = query_sims[i]
                # Max similarity to any already-selected wine
                redundancy = max(
                    cand_vecs[i] @ selected_vecs[j] / (
                        np.linalg.norm(cand_vecs[i]) * np.linalg.norm(selected_vecs[j]) + 1e-10
                    )
                    for j in range(len(selected_indices))
                )
                scores.append((i, lambda_param * relevance - (1 - lambda_param) * redundancy))
            best = max(scores, key=lambda x: x[1])[0]

        selected_indices.append(best)
        remaining.remove(best)

    return [candidates[i] for i in selected_indices]