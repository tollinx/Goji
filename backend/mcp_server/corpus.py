"""The drink corpus and similarity search over it.

The corpus is a small static JSON file, so the whole index is just an array of
normalized embeddings held in memory. It's built lazily on the first search and
cached for the life of the process — there's no ingestion pipeline and no
vector database.
"""

import json
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).parent / "data" / "drinks.json"
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


@dataclass(frozen=True)
class Corpus:
    drinks: list[dict]
    embeddings: np.ndarray
    model: SentenceTransformer


@cache
def _corpus() -> Corpus:
    """Load the drinks and embed them. Cached, so this runs at most once."""
    drinks = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(
        [drink["search_text"] for drink in drinks],
        normalize_embeddings=True,
    )
    return Corpus(drinks=drinks, embeddings=embeddings, model=model)


def search(query: str, top_k: int = 3) -> list[dict]:
    """Return the top_k drinks ranked by cosine similarity to the query."""
    corpus = _corpus()

    # Embeddings are normalized, so a dot product is the cosine similarity.
    query_embedding = corpus.model.encode([query], normalize_embeddings=True)[0]
    scores = corpus.embeddings @ query_embedding

    return [
        {
            "id": corpus.drinks[i]["id"],
            "name": corpus.drinks[i]["name"],
            "tasting_notes": corpus.drinks[i]["tasting_notes"],
            "mood_tags": corpus.drinks[i]["mood_tags"],
            "score": round(float(scores[i]), 4),
        }
        for i in np.argsort(-scores)[:top_k]
    ]


def get(drink_id: str) -> dict | None:
    """Return the full recipe for a drink id, or None if it doesn't exist."""
    return next((d for d in _corpus().drinks if d["id"] == drink_id), None)
