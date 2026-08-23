import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# Load embedding model
print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def ingest_catalog():
    products_file = os.path.join("data", "products.json")
    if not os.path.exists(products_file):
        print(f"Error: {products_file} does not exist. Run generate_products.py first.")
        return

    with open(products_file, "r") as f:
        products = json.load(f)

    # Initialize ChromaDB client
    db_path = os.path.abspath("./chroma_db")
    os.makedirs(db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=db_path)

    # Recreate the collection (allows rebuilding the index)
    collection_name = "merchant_catalog"
    try:
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass

    collection = client.create_collection(name=collection_name)
    print(f"Created collection: {collection_name}")

    documents = []
    embeddings = []
    metadatas = []
    ids = []

    for product in products:
        pid = product["product_id"]
        name = product["name"]
        brand = product["brand"]
        category = product["category"]
        desc = product["description"]
        price = product["price"]
        inventory = product["inventory"]
        tags = product["tags"]
        discount = product["discount"]
        rating = product["rating"]
        popularity = product["popularity"]
        comps = product["complementary_products"]
        img = product["image"]
        url = product["product_url"]

        # Build clean semantic representation
        text_repr = (
            f"Name: {name}\n"
            f"Brand: {brand}\n"
            f"Category: {category}\n"
            f"Description: {desc}\n"
            f"Tags: {', '.join(tags)}\n"
            f"Price: INR {price}\n"
            f"Rating: {rating}/5\n"
        )

        print(f"Embedding product: {pid} - {name}")
        embedding = embedding_model.encode(text_repr).tolist()

        # ChromaDB metadata must be string, int, float, or bool
        metadata = {
            "product_id": pid,
            "name": name,
            "brand": brand,
            "category": category,
            "price": float(price),
            "inventory": int(inventory),
            "discount": float(discount),
            "rating": float(rating),
            "popularity": float(popularity),
            "tags": ",".join(tags),
            "complementary_products": ",".join(comps),
            "image": img,
            "product_url": url,
            "in_stock": int(inventory > 0)
        }

        documents.append(text_repr)
        embeddings.append(embedding)
        metadatas.append(metadata)
        ids.append(pid)

    # Add all in one batch
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Ingested {len(products)} products into ChromaDB merchant_catalog collection successfully!")

if __name__ == "__main__":
    ingest_catalog()
