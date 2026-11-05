# `metermind.retrieval`

This package turns tariff documents into searchable, date/category-filterable evidence.

- `__init__.py`: package marker.
- `document_loader.py`: extracts text from tariff PDFs and loads order metadata from a manifest.
- `chunking.py`: cuts orders into overlapping chunks and carries order/effective-date/category/section metadata.
- `vector_store.py`: embeds chunks into a persistent Chroma collection and performs similarity search.
- `filtered_search.py`: selects the tariff order in force for a category and billing period, restricts vector search to that order, and writes answers with the governing order ID.
- `grounded_answer.py`: asks the language model to answer only from retrieved chunks and verifies citations.

The assistant's `search_tariff_order` tool uses this pipeline. A missing vector store, manifest, model, or tariff artifact must be handled during deployment.
