---
name: golden-set-authoring
description: >
  Author, validate, or extend the golden evaluation set in backend/evals/golden_set.jsonl.
  Use whenever adding new Q&A eval examples, reviewing eval quality, or writing tasks
  that touch golden_set.jsonl. Auto-invoke when the user says "add eval questions",
  "extend the golden set", or "write test cases for the RAG."
---

# Golden set authoring procedure

## What the golden set IS
The primary sellable artifact of this project. Every compliance answer we make is
legally load-bearing. The golden set is the ground truth that makes the Ragas eval
harness meaningful. Treat it with the rigor of a test suite, not a demo script.

## JSONL schema — one JSON object per line
```json
{
  "question":       "What does AC-2 require organizations to do?",
  "answer":         "AC-2 requires organizations to define, document, and manage information system accounts including establishing account types, assigning account managers, setting conditions for group membership, and specifying authorized users.",
  "source_control": "AC-2",
  "framework":      "NIST-800-53",
  "source_doc":     "nist_800_53_rev5.pdf",
  "page":           35,
  "question_type":  "factual",
  "difficulty":     "easy"
}
```

## Question types to cover (target distribution for 100-question set)
- **factual** (40%): "What does [CONTROL-ID] require?" Direct requirement lookup.
- **multi-hop** (25%): "How do AC-2 and AC-3 together control privileged access?"
  Requires synthesizing two controls.
- **negative** (20%): Questions the system should ABSTAIN on — out-of-scope topics,
  ambiguous phrasing, or topics not covered in the indexed corpus.
- **exact-id** (15%): Queries using exact control IDs like "AC-2(3)" or "SI-7(1)".
  These test BM25/keyword retrieval specifically.

## Quality bar for each triple
1. **Answer is grounded in the source document** — no paraphrasing that changes meaning.
   Copy key phrases verbatim from the control text; acceptable to condense discussion.
2. **Source is specific** — control_id + page number, not just "NIST 800-53."
3. **Negative examples are genuinely unanswerable** from the corpus — don't make them
   trick questions, make them honest out-of-scope probes.
4. **Difficulty is calibrated** — easy = single control lookup; medium = two controls
   or a specific enhancement; hard = cross-framework or implicit requirement.

## Authoring workflow when adding new questions
1. Pull the relevant control text from the parsed chunks in
   `backend/ingestion/chunks/`.
2. Write the question first, then derive the answer from the source text.
   Never write answer-first; that biases toward what sounds right vs. what is true.
3. For negative examples, verify the topic is genuinely absent from the chunks
   before labeling it a negative.
4. Append to `backend/evals/golden_set.jsonl` — never overwrite.
5. After adding ≥10 new entries, run `python backend/evals/run_evals.py --quick`
   to confirm the new entries are parseable and the harness isn't broken.

## Coverage targets
Aim for at least 10 questions per control family (AC, AT, AU, CA, CM, IA, IR, MA,
MP, PE, PL, PM, PS, PT, RA, SA, SC, SI, SR). Gaps in family coverage = gaps in
demo credibility.