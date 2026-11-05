"""Accuracy is one number. The champion is reported class by class, with confusion behind it."""

from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from config import constants

EXCEPTION_CLASSES = constants.EXCEPTION_CLASSES
EXCEPTION_REPORT_FIELDS = ("exception_class", "precision", "recall", "support")


def per_class_scores(truth, predicted):
    precisions, recalls, _, supports = precision_recall_fscore_support(
        truth, predicted, labels=list(EXCEPTION_CLASSES), zero_division=0
    )
    return {
        name: {"precision": float(precision), "recall": float(recall), "support": int(support)}
        for name, precision, recall, support in zip(EXCEPTION_CLASSES, precisions, recalls, supports)
    }


def confusion_frame(truth, predicted):
    matrix = confusion_matrix(truth, predicted, labels=list(EXCEPTION_CLASSES))
    return pd.DataFrame(matrix, index=list(EXCEPTION_CLASSES), columns=list(EXCEPTION_CLASSES))


def write_exception_report(truth, predicted, where):
    scores = per_class_scores(truth, predicted)

    where = Path(where)
    where.parent.mkdir(parents=True, exist_ok=True)

    total_support = sum(one["support"] for one in scores.values())
    with open(where, "w", encoding="utf-8") as handle:
        handle.write(",".join(EXCEPTION_REPORT_FIELDS) + "\n")
        for name in EXCEPTION_CLASSES:
            one = scores[name]
            handle.write(
                f"{name},{round(one['precision'], 4)},{round(one['recall'], 4)},"
                f"{one['support']}\n"
            )
        handle.write(f"TOTAL,,,{total_support}\n")

    return where


if __name__ == "__main__":
    from metermind.exception_models.baseline_model import load_model, split_readings
    from metermind.exception_models.feature_engineering import widen_readings
    from metermind.exception_models.feature_pipeline import modelling_columns

    book = widen_readings(pd.read_csv(constants.CLEAN_READING_BOOK_PATH))
    _, held_out_columns, _, held_out_classes = split_readings(book, modelling_columns(True))

    champion = load_model(constants.CHAMPION_MODEL_PATH)
    predicted = champion.predict(held_out_columns)

    print(confusion_frame(held_out_classes, predicted))
    written = write_exception_report(held_out_classes, predicted, constants.EXCEPTION_REPORT_PATH)
    print(f"written: {written}")
