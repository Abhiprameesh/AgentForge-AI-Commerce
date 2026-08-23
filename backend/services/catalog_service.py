import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
print("Loading catalog embedding model (all-MiniLM-L6-v2)...")
try:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Warning: Failed to load sentence transformer model: {e}")
    embedding_model = None

# Initialize ChromaDB
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db"))
try:
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="merchant_catalog")
except Exception as e:
    print(f"Warning: Failed to initialize ChromaDB: {e}")
    chroma_client = None
    collection = None

# Load products from JSON into memory for deterministic operations
products_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "products.json"))

_products_cache = {}
try:
    if os.path.exists(products_path):
        with open(products_path, "r") as f:
            data = json.load(f)
            for p in data:
                _products_cache[p["product_id"]] = p
        print(f"Loaded {len(_products_cache)} products into memory cache.")
    else:
        print(f"Warning: products.json not found at {products_path}")
except Exception as e:
    print(f"Error loading products.json: {e}")

def get_product(product_id: str) -> dict | None:
    """Return product details from memory cache."""
    return _products_cache.get(product_id)

def get_all_products() -> list[dict]:
    """Return all products in the catalog."""
    return list(_products_cache.values())

def search_products(query: str, limit: int = 4, category: str | None = None, max_price: float | None = None) -> list[dict]:
    """
    Search catalog using ChromaDB for semantic retrieval.
    Apply deterministic filters in memory to guarantee accuracy.
    """
    if not query:
        # If query is empty, return filtered list sorted by popularity
        results = get_all_products()
    else:
        if collection and embedding_model:
            try:
                query_embedding = embedding_model.encode(query).tolist()
                chroma_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit * 2  # Fetch more to allow filtering
                )
                
                # Fetch matching products from memory cache
                matched_ids = chroma_results["ids"][0] if chroma_results["ids"] else []
                results = []
                for pid in matched_ids:
                    prod = get_product(pid)
                    if prod:
                        results.append(prod)
            except Exception as e:
                print(f"Semantic search error: {e}. Falling back to keyword search.")
                # Fallback to simple keyword search
                results = _keyword_search(query)
        else:
            results = _keyword_search(query)

    # Apply deterministic filters in-memory (price, category)
    filtered_results = []
    for prod in results:
        # Category Filter
        if category and category.lower() != "all" and prod["category"].lower() != category.lower():
            continue
        # Max Price Filter
        if max_price is not None and prod["price"] > max_price:
            continue
        filtered_results.append(prod)

    return filtered_results[:limit]

def _keyword_search(query: str) -> list[dict]:
    """Simple keyword matching fallback when vector database is unavailable."""
    query_words = query.lower().split()
    matched = []
    for prod in get_all_products():
        score = 0
        name_lower = prod["name"].lower()
        desc_lower = prod["description"].lower()
        brand_lower = prod["brand"].lower()
        tags_lower = [t.lower() for t in prod["tags"]]
        
        for word in query_words:
            if word in name_lower:
                score += 5
            if word in brand_lower:
                score += 3
            if word in desc_lower:
                score += 1
            for tag in tags_lower:
                if word in tag:
                    score += 2
                    
        if score > 0:
            matched.append((score, prod))
            
    # Sort by score desc, then popularity desc
    matched.sort(key=lambda x: (-x[0], -x[1]["popularity"]))
    return [item[1] for item in matched]
