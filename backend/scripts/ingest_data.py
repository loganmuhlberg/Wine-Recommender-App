"""
ingest_data.py

One time script that reads in the data from data/wine_db.csv embeds each 
wine description using a sentence transformer, and stores the result
in a ChromaDB vector database.
"""
import argparse
import os
import sys
import time
import pandas as pd
import chromadb
 
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

### Configuration

# Paths are relative to the backend/ directory (where you run the script from)
DEFAULT_CSV_PATH   = "../data/wines_db.csv"
CHROMA_DB_PATH     = "../wine_db"
COLLECTION_NAME    = "wines"
 
# Embedding model from huggingface, used to embed the description of every wine,
# and store that description in the ChromaDB database so that it can be searched for
# similarity with the user query and taste profile information.
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"
 
# How many wines to embed and upsert in one batch.
# 100 is a safe default for CPU. Raise to 250-500 if you have a GPU.
DEFAULT_BATCH_SIZE = 100
 
# Minimum description length: wines with fewer characters than this
# are skipped since there's not enough text to produce a useful embedding.
MIN_DESCRIPTION_LENGTH = 50


### Parsers

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest Kaggle wine reviews into ChromaDB."
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to the Kaggle CSV file (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Embedding batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only ingest the first N rows. Useful for testing.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing ChromaDB collection and rebuild from scratch.",
    )
    return parser.parse_args()
 

### Data Loading and Cleaning:

def load_csv(path : str, limit : int = None) -> pd.DataFrame:
    """
    Loads the wine review dataset and preprocesses,
    so that it is ready for embedding.
    """
    print(f"\nLoading CSV from: {path}")
 
    if not os.path.exists(path):
        print(f"ERROR: File not found at '{path}'")
        print("Make sure wines_db.csv is in your data/ directory.")
        sys.exit(1)
 
    df = pd.read_csv(path)

    print(f"  Raw rows loaded:       {len(df):,}")

    # Drop rows where description is missing or too short to be useful
    df = df.dropna(subset=["description"])
    df = df[df["description"].str.len() >= MIN_DESCRIPTION_LENGTH]
    print(f"  After description filter: {len(df):,}")
 
    # Deduplicate on description text — some wines appear multiple times
    df = df.drop_duplicates(subset=["description"])
    print(f"  After deduplication:   {len(df):,}")

    # Reset index, cleaner for ID setting in ChromaDB
    df = df.reset_index(drop=True)

    if limit:
        df = df.head(limit)
        print(f"  Limiting to first {limit:,} rows for testing")
 
    return df

def build_embed_text(row : pd.Series) -> str:
    """
    Construct the text to embed for a single wine.
 
    Text is created by combining title with the description,
    so that the model similarity has more information and is more accurate.
    This aims to capture the identity of the wine (varietal, region), as well
    as the general taste.
    """
    parts = []
 
    if pd.notna(row.get("title")) and str(row["title"]).strip():
        parts.append(str(row["title"]).strip())
 
    if pd.notna(row.get("variety")) and str(row["variety"]).strip():
        parts.append(str(row["variety"]).strip())
 
    if pd.notna(row.get("description")) and str(row["description"]).strip():
        parts.append(str(row["description"]).strip())
 
    return ". ".join(parts)

def build_metadata(row: pd.Series) -> dict:
    """
    Build the ChromaDB metadata dictionary for a single wine.
 
    Rules:
    - All values must be str, int, or float — ChromaDB doesn't accept None.
    - Use -1.0 for unknown price and 0 for unknown points so range filters
      don't crash. Callers should filter out price == -1.0 when the user
      has set a price ceiling.
    - Truncate long string fields to avoid bloating the metadata store.
    """
    def safe_str(val, max_len: int = 200) -> str:
        if pd.isna(val) or str(val).strip() == "":
            return ""
        return str(val).strip()[:max_len]
 
    def safe_float(val, fallback: float = -1.0) -> float:
        try:
            f = float(val)
            return f if not pd.isna(f) else fallback
        except (TypeError, ValueError):
            return fallback
 
    def safe_int(val, fallback: int = 0) -> int:
        try:
            i = int(val)
            return i if not pd.isna(float(val)) else fallback
        except (TypeError, ValueError):
            return fallback
 
    return {
        "title":       safe_str(row.get("title")),
        "winery":      safe_str(row.get("winery")),
        "variety":     safe_str(row.get("variety")),
        "country":     safe_str(row.get("country")),
        "province":    safe_str(row.get("province")),
        "region_1":    safe_str(row.get("region_1")),
        "designation": safe_str(row.get("designation")),
        "description": safe_str(row.get("description"), max_len=1000),
        "points":      safe_int(row.get("points")),
        "price":       safe_float(row.get("price")),
    }

### ChromaDB Setup

def get_or_create_collection(
    chroma_path: str,
    collection_name: str,
    reset: bool,
) -> tuple[chromadb.PersistentClient, chromadb.Collection]:
    """
    Connect to (or create) the persistent ChromaDB collection.
    If reset=True, deletes the existing collection first.
    """
    print(f"\nConnecting to ChromaDB at: {chroma_path}")
    client = chromadb.PersistentClient(path=chroma_path)
 
    #If reset=True, try to delete current collection, unless it does not exist yet.
    if reset:
        try:
            client.delete_collection(collection_name)
            print(f"  Deleted existing '{collection_name}' collection.")
        except Exception:
            pass  
 
    #Get or create the ChromaDB collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}, #sets distance metric to cosine
    )
    
    #Test to see how many rows have been ingested.
    existing_count = collection.count()
    print(f"  Collection '{collection_name}': {existing_count:,} existing documents")
    return client, collection
 

def get_already_ingested_ids(collection: chromadb.Collection) -> set[str]:
    """
    Return the set of document IDs already present in the collection.
    Used for resumable ingestion. If the script is re-run after a crash,
    already-processed wines are skipped rather than re-embedded.
    """
    existing = collection.count()
    if existing == 0:
        return set()
 
    print(f"  Fetching existing IDs for resume support...")
    # ChromaDB requires fetching in chunks for large collections
    all_ids = set()
    offset = 0
    chunk_size = 5000
    while True:
        result = collection.get(limit=chunk_size, offset=offset, include=[])
        if not result["ids"]:
            break
        all_ids.update(result["ids"])
        offset += chunk_size
        if offset >= existing:
            break
 
    print(f"  Found {len(all_ids):,} already-ingested IDs")
    return all_ids
 
 
### Ingestion Loop

def ingest(
    df: pd.DataFrame,
    collection: chromadb.Collection,
    model: SentenceTransformer,
    batch_size: int,
    already_ingested: set[str],
) -> None:
    """
    Embed and upsert wines in batches.
    Skips wines already present in the collection (resume support).
    """
    # Filter to only rows that haven't been ingested yet
    rows_to_process = [
        (idx, row) for idx, row in df.iterrows()
        if f"wine_{idx}" not in already_ingested
    ]
 
    if not rows_to_process:
        print("\nAll wines already ingested — nothing to do.")
        return
 
    print(f"\nIngesting {len(rows_to_process):,} wines in batches of {batch_size}...")
    print("(This will take a while on first run. Progress is saved — safe to Ctrl+C and resume.)\n")
 
    skipped = 0
    total_batches = (len(rows_to_process) + batch_size - 1) // batch_size
    start_time = time.time()
 
    # Shows progress meter for batches, should be 2810 if starting from scratch.
    for batch_num in tqdm(range(total_batches), desc="Batches", unit="batch"):
        batch_start = batch_num * batch_size
        batch_rows  = rows_to_process[batch_start : batch_start + batch_size]
 
        ids       = []
        texts     = []
        metadatas = []
        documents = []
 
        for idx, row in batch_rows:
            embed_text = build_embed_text(row)
 
            # skip if there's nothing to embed
            if not embed_text.strip():
                skipped += 1
                continue
 
            ids.append(f"wine_{idx}")
            texts.append(embed_text)
            metadatas.append(build_metadata(row))
            documents.append(str(row.get("description", "")))
 
        if not ids:
            continue
 
        # Embed the batch
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
 
        # Upsert into ChromaDB (upsert = insert or update if ID exists)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
 
    elapsed = time.time() - start_time
    final_count = collection.count()
 
    print(f"\n{'='*55}")
    print(f"  Ingestion complete")
    print(f"  Wines in collection: {final_count:,}")
    print(f"  Skipped (empty text): {skipped:,}")
    print(f"  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"{'='*55}")

### Testing Function

def test_encoding(collection: chromadb.Collection, model: SentenceTransformer) -> None:
    """
    Run two quick queries to verify the collection is working correctly, and that the similarity based
    embedding method returns reasonable results.
    """
    print("\nRunning tests...\n")
 

    #Test for two different scenarios: One without filters, one with.
    tests = [
        {
            "label": "Semantic: bold red with dark fruit",
            "query": "bold full-bodied red wine with dark fruit cherry oak tannins",
            "filter": None,
        },
        {
            "label": "Semantic + price filter: crisp white under $20",
            "query": "crisp dry white wine citrus mineral refreshing",
            "filter": {"$and": [{"price": {"$gte": 0}}, {"price": {"$lte": 20}}]},
        },
    ]
 
    for test in tests:
        print(f"  Query: \"{test['label']}\"")
        query_embedding = model.encode([test["query"]]).tolist()
 
        kwargs = {
            "query_embeddings": query_embedding,
            "n_results": 3,
            "include": ["documents", "metadatas", "distances"],
        }
        if test["filter"]:
            kwargs["where"] = test["filter"]
 
        results = collection.query(**kwargs)
 
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            print(f"    #{i+1} {meta['title'] or meta['winery']} "
                  f"({meta['variety']}) "
                  f"${meta['price']:.0f} | {meta['points']}pts | "
                  f"similarity: {1 - dist:.3f}")
            print(f"         {doc[:100]}...")
        print()
 
 

### Run Ingestion Pipeline

if __name__ == "__main__":
    args = parse_args()
 
    # 1. Load and clean the CSV
    df = load_csv(args.csv, args.limit)
 
    # 2. Load the embedding model
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("  (First run downloads ~90MB — subsequent runs are instant)")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("  Model loaded.")
 
    # 3. Connect to ChromaDB
    client, collection = get_or_create_collection(
        CHROMA_DB_PATH, COLLECTION_NAME, args.reset
    )
 
    # 4. Get already-ingested IDs for resume support
    already_ingested = get_already_ingested_ids(collection)
 
    # 5. Run ingestion
    ingest(df, collection, model, args.batch_size, already_ingested)
 
    # 6. Smoke test
    if collection.count() > 0:
        test_encoding(collection, model)
    else:
        print("\nCollection is empty: test skipped.")

 


