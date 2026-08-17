---
name: control-chunking
description: >
  Parse NIST 800-53, CMMC, FedRAMP, or any security-controls framework PDF
  into retrieval-ready chunks. Use whenever ingesting a compliance document,
  adding a new corpus to the RAG index, or writing/editing backend/ingestion/parse.py
  or backend/ingestion/embed_and_load.py. Auto-invoke on any task that involves
  chunking, parsing compliance PDFs, or onboarding a new control framework.
---

# Control-aware chunking procedure

## Core rule
Split by **control**, not by fixed token window. One control = one retrieval unit.
Never merge controls into a single chunk, never split one control across chunks.

## Chunk metadata schema (attach to every chunk)
```json
{
  "control_id":       "AC-2",
  "family":           "Access Control",
  "title":            "Account Management",
  "framework":        "NIST-800-53",
  "requirement_text": "...",
  "discussion":       "...",
  "source_doc":       "nist_800_53_rev5.pdf",
  "page_range":       "pp. 34-37"
}
```

## Parsing steps

1. **Detect framework type** from filename or first-page header. NIST 800-53 controls
   follow the pattern `[FAMILY_CODE]-[NUMBER]` (e.g. AC-2, SI-7). CMMC practices
   follow `[DOMAIN].[LEVEL].[PRACTICE]` (e.g. AC.1.001). FedRAMP inherits NIST IDs.

2. **Split on control boundaries.** In NIST 800-53 Rev5 PDFs, control blocks begin with
   the bolded control ID heading. Use regex `^[A-Z]{2}-\d+(\s\([0-9]+\))?` as the
   boundary marker. For CMMC, split on practice ID headings.

3. **Keep the control ID verbatim** in the chunk text (not just metadata). BM25/keyword
   search must be able to match exact queries like "AC-2" — if the ID is only in
   metadata it won't surface in hybrid retrieval.

4. **Separate requirement from discussion.** The "Control" paragraph is requirement_text;
   the "Discussion" section is discussion. Store both but index requirement_text
   as the primary field.

5. **Emit JSONL**, one JSON object per line, schema above. Output file:
   `backend/ingestion/chunks/<framework_slug>_chunks.jsonl`

## Quality checks before calling embed_and_load.py
- Every chunk must have a non-null control_id and requirement_text
- No chunk should exceed 800 tokens (split enhancement sections if needed)
- Control ID must appear in the chunk text string, not only in metadata
- Run a quick dedup check — some PDFs repeat controls in appendices