from pypdf import PdfReader

import chromadb

from sentence_transformers import (
    SentenceTransformer
)

# Embedding model
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

# Persistent ChromaDB
client = chromadb.PersistentClient(
    path="./research_db"
)

collection = client.get_or_create_collection(
    name="research_papers"
)

# Extract text from PDF
def extract_pdf_text(file_path):

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:

        text += page.extract_text()

    return text
# Chunk text
def chunk_text(text, chunk_size=500):

    chunks = []

    for i in range(0, len(text), chunk_size):

        chunks.append(
            text[i:i + chunk_size]
        )

    return chunks

# Store research paper
def store_research_paper(file_path):

    text = extract_pdf_text(file_path)

    chunks = chunk_text(text)

    for idx, chunk in enumerate(chunks):

        embedding = embedding_model.encode(
            chunk
        ).tolist()

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{file_path}_{idx}"]
        )

# Retrieve relevant chunks
def retrieve_research_context(query):

    query_embedding = embedding_model.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    return results["documents"][0]