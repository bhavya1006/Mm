# `metermind.exception_models`

This package trains and serves classifiers for reading exceptions such as high usage, estimated reads, meter faults, tampering, and tariff mismatches.

- `__init__.py`: package marker.
- `baseline_model.py`: logistic-regression pipeline, train/test split, scoring, model persistence, and prediction.
- `champion_model.py`: compares eligible models, chooses a champion, optimizes an error-cost operating rule, and persists both.
- `cross_validation.py`: evaluates baseline, tree, forest, and support-vector candidates across stratified folds.
- `exception_report.py`: writes per-class precision/recall/support and confusion information.
- `feature_engineering.py`: adds consumption-to-average ratio, load factor, and meter age.
- `feature_pipeline.py`: defines numeric/category feature columns and shared imputation, scaling, and one-hot encoding.
- `investigation_queues.py`: maps predictions into named queues, counts them, and writes queue CSVs.
- `tree_models.py`: builds/trains decision-tree and random-forest alternatives and compares class weighting.

The `/screening` route uses the saved champion, operating rule, feature engineering, and queue mapping.
