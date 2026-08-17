Scrape and chunk web content into retrieval-ready JSONL for the film corpus. Use whenever working on backend/ingestion/scrape_web.py, adding new film sources (Criterion essays, Ebert reviews, director interviews), or ingesting any web-based corpus into Kurai. Auto-invoke on any task involving web scraping, film corpus ingestion, or URL-based document processing.

Web content chunking procedure
Sources and their structure

Criterion Collection essays (criterion.com/current)

Each essay is one coherent piece — chunk as a single unit if under 600 tokens
If over 600 tokens, split at paragraph boundaries, never mid-sentence
URL pattern: criterion.com/current/posts/<slug>
Metadata: author, title, film_title, director, publication_date, url

Roger Ebert reviews (rogerebert.com/reviews)

Each review is one chunk — Ebert's reviews are typically 400-800 tokens, perfect size
Metadata: film_title, director, star_rating, publication_date, url
The star rating goes in metadata — don't embed it in chunk_text or it skews semantic search

Director interviews (various sources — Criterion, IndieWire, BFI)

Split by Q&A exchange, not by arbitrary length
One question + answer = one chunk
Keep the interviewer question in the chunk — it's context for the answer
Metadata: director, interviewer, source_publication, publication_date, url, film_title (if interview is film-specific)
Chunk metadata schema
json
{
  "director":          "Wong Kar-wai",
  "film_title":        "In the Mood for Love",
  "content_type":      "essay | review | interview",
  "source":            "Criterion | Ebert | BFI | IndieWire",
  "author":            "Text by Tony Rayns",
  "publication_date":  "2002-03-15",
  "url":               "https://criterion.com/current/posts/...",
  "star_rating":       4.0
}
Scraping rules
Respect robots.txt — check before scraping any source
Rate limit requests — 1 request per 2 seconds minimum, no parallel scraping
Use requests + BeautifulSoup for static pages; playwright only if JS rendering required
Strip navigation, ads, footers — extract article body only
Preserve paragraph breaks as \n\n in chunk_text — they're semantic signals
Store raw HTML alongside JSONL during development for debugging — delete before committing
Output

Emit JSONL to backend/ingestion/chunks/film_chunks.jsonl, one JSON object per line:

json
{
  "chunk_text": "...",
  "metadata": { ... },
  "source_doc": "https://criterion.com/current/posts/...",
  "project_slug": "film"
}
Quality checks before embed_and_load.py
No chunk under 50 tokens (probably a nav element that wasn't stripped)
No chunk over 800 tokens (split it)
Every chunk has a non-null url in metadata (needed for citations)
director field populated — this is the primary retrieval signal for film queries
Run dedup on url — some sources republish content under multiple URLs