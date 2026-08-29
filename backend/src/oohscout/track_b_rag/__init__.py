"""Track B — Regulatory RAG.

Document retrieval over billboard regulations. Always returns citation.
Modules (to be built):
- corpus: document ingestion with provenance
- chunker: section-metadata-aware chunking
- retriever: pgvector + BM25 hybrid retrieval
- extractor: structured rule extraction to verified_rules JSON
- verified_rules: human review workflow (draft -> verified)
"""
