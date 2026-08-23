import chromadb

from sentence_transformers import (
    SentenceTransformer
)

import hashlib

client = chromadb.PersistentClient(
    path="agent_memory_db"
)


collection = client.get_or_create_collection(
    name="agent_memory"
)

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def store_agent_memory(
    agent_type,
    text
):

    embedding = embedding_model.encode(
        text
    ).tolist()

    mem_id = hashlib.md5(text.encode("utf-8")).hexdigest()

    collection.add(
        documents=[text],
        embeddings=[embedding],
        metadatas=[
            {
                "agent": agent_type
            }
        ],
        ids=[mem_id]
    )


def retrieve_agent_memory(
    agent_type,
    query,
    n_results=3
):

    query_embedding = embedding_model.encode(
        query
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={
            "agent": agent_type
        }
    )

    return results["documents"][0]