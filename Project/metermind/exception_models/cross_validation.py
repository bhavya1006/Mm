"""A fourth family, and a comparison that does not rest on one lucky split."""

from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from config import constants
from metermind.exception_models.baseline_model import build_baseline_model
from metermind.exception_models.feature_pipeline import build_feature_pipeline
from metermind.exception_models.tree_models import build_decision_tree_model, build_random_forest_model

CROSS_VALIDATION_FIELDS = ("model", "fold", "accuracy")


def build_support_vector_model(class_weight=None, widened=False):
    return Pipeline([
        ("prepare", build_feature_pipeline(widened)),
        ("decide", LinearSVC(
            C=constants.SUPPORT_VECTOR_REGULARISATION, class_weight=class_weight,
            random_state=constants.MODEL_SEED, max_iter=10000,
        )),
    ])


def every_candidate_model(class_weight=None, widened=False):
    return {
        "baseline": build_baseline_model(class_weight, widened),
        "decision_tree": build_decision_tree_model(class_weight, widened),
        "random_forest": build_random_forest_model(class_weight, widened),
        "support_vector": build_support_vector_model(class_weight, widened),
    }


def cross_validate_models(fitting_columns, fitting_classes, folds=None):
    fold_count = folds if folds is not None else constants.CROSS_VALIDATION_FOLDS
    splitter = StratifiedKFold(n_splits=fold_count, shuffle=True, random_state=constants.MODEL_SEED)

    scored = {}
    for name, model in every_candidate_model().items():
        fold_scores = cross_val_score(
            model, fitting_columns, fitting_classes, cv=splitter, n_jobs=1,
        )
        scored[name] = [float(one) for one in fold_scores]
    return scored


def fold_spread(fold_scores):
    return max(fold_scores) - min(fold_scores)


def write_cross_validation(scored, where):
    where = Path(where)
    where.parent.mkdir(parents=True, exist_ok=True)

    with open(where, "w", encoding="utf-8") as handle:
        handle.write(",".join(CROSS_VALIDATION_FIELDS) + "\n")
        for name, fold_scores in scored.items():
            for fold_number, score in enumerate(fold_scores, start=1):
                handle.write(f"{name},{fold_number},{score}\n")

    return where


if __name__ == "__main__":
    import pandas as pd
    from metermind.exception_models.baseline_model import split_readings

    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    fitting_columns, _, fitting_classes, _ = split_readings(book)

    scored = cross_validate_models(fitting_columns, fitting_classes)
    write_cross_validation(scored, constants.CROSS_VALIDATION_PATH)

    for name, fold_scores in scored.items():
        mean = sum(fold_scores) / len(fold_scores)
        print(f"{name:<16} mean {round(mean, 4)}  spread {round(fold_spread(fold_scores), 4)}")
