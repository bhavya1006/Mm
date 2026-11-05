"""The baseline exception classifier, and the split every later comparison shares."""

import json
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

import pandas as pd

from config import constants
from metermind.exception_models.feature_pipeline import (
    EXCEPTION_COLUMN,
    MODELLING_COLUMNS,
    build_feature_pipeline,
)

EXCEPTION_CLASSES = constants.EXCEPTION_CLASSES
FITTING_ROUNDS_LIMIT = 1000


def split_readings(book, columns=None):
    columns_wanted = list(columns) if columns is not None else list(MODELLING_COLUMNS)
    feature_columns = book[columns_wanted]
    classes = book[EXCEPTION_COLUMN]
    return train_test_split(
        feature_columns, classes, test_size=constants.HELD_OUT_SHARE,
        random_state=constants.MODEL_SEED, stratify=classes,
    )


def build_baseline_model(class_weight=None, widened=False):
    return Pipeline([
        ("prepare", build_feature_pipeline(widened)),
        ("decide", LogisticRegression(
            max_iter=FITTING_ROUNDS_LIMIT, class_weight=class_weight,
            random_state=constants.MODEL_SEED,
        )),
    ])


def train_baseline_model(fitting_columns, fitting_classes):
    model = build_baseline_model()
    model.fit(fitting_columns, fitting_classes)
    return model


def score_exception_model(model, held_out_columns, held_out_classes):
    predicted = model.predict(held_out_columns)
    accuracy = float(accuracy_score(held_out_classes, predicted))

    precisions, recalls, _, _ = precision_recall_fscore_support(
        held_out_classes, predicted, labels=list(EXCEPTION_CLASSES), zero_division=0
    )
    per_class = {
        name: {"precision": float(precision), "recall": float(recall)}
        for name, precision, recall in zip(EXCEPTION_CLASSES, precisions, recalls)
    }

    return {"accuracy": accuracy, "per_class": per_class}


def save_model(model, model_path):
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return model_path


def load_model(model_path):
    return joblib.load(model_path)


def predict_exception(model, readings):
    return list(model.predict(readings[list(MODELLING_COLUMNS)]))


if __name__ == "__main__":
    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    fitting_columns, held_out_columns, fitting_classes, held_out_classes = split_readings(book)
    trained = train_baseline_model(fitting_columns, fitting_classes)
    scored = score_exception_model(trained, held_out_columns, held_out_classes)

    save_model(trained, constants.BASELINE_MODEL_PATH)
    Path(constants.BASELINE_SCORES_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(constants.BASELINE_SCORES_PATH).write_text(json.dumps(scored, indent=2))

    print(f"accuracy: {round(scored['accuracy'], 4)}")



def score_exception_model(model, held_out_columns, held_out_classes):
    predicted = model.predict(held_out_columns)
    accuracy = float(accuracy_score(held_out_classes, predicted))

    precisions, recalls, _, _ = precision_recall_fscore_support(
        held_out_classes, predicted, labels=list(EXCEPTION_CLASSES), zero_division=0
    )
    per_class = {
        name: {"precision": float(precision), "recall": float(recall)}
        for name, precision, recall in zip(EXCEPTION_CLASSES, precisions, recalls)
    }

    return {"accuracy": accuracy, "per_class": per_class}


def save_model(model, model_path):
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return model_path


def load_model(model_path):
    return joblib.load(model_path)


def predict_exception(model, readings):
    return list(model.predict(readings[list(MODELLING_COLUMNS)]))


if __name__ == "__main__":
    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    fitting_columns, held_out_columns, fitting_classes, held_out_classes = split_readings(book)
    trained = train_baseline_model(fitting_columns, fitting_classes)
    scored = score_exception_model(trained, held_out_columns, held_out_classes)

    save_model(trained, constants.BASELINE_MODEL_PATH)
    Path(constants.BASELINE_SCORES_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(constants.BASELINE_SCORES_PATH).write_text(json.dumps(scored, indent=2))

    print(f"accuracy: {round(scored['accuracy'], 4)}")
