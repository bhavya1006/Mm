# `metermind.message_intelligence`

This package processes consumer complaints and conversation threads.

- `__init__.py`: package marker.
- `attention.py`: small NumPy implementation of softmax and scaled dot-product attention.
- `batch_pipeline.py`: applies a handler across messages while recording failures and continuing.
- `complaint_classifier.py`: trains TF-IDF/logistic-regression classifiers for complaint category and urgency.
- `escalation.py`: combines complaint age, predicted urgency, and LLM-read tone into an escalation decision.
- `llm_client.py`: loads Gemini settings, caches model answers, parses JSON responses, and retries model failures.
- `reference_extraction.py`: extracts account, meter, and complaint references and checks them against a connection register.
- `text_cleaning.py`: removes quoted replies, greetings, sign-offs, signatures, references, and excess whitespace.
- `thread_summary.py`: selects salient sentences with attention and writes one summary per thread.

These workflows are primarily batch/offline utilities. The assistant reuses `llm_client` indirectly for its model prompts.
