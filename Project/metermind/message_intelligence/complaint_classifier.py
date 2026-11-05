"""Two classifiers over the complaint corpus."""

import json
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from config import constants
from metermind.message_intelligence.text_cleaning import clean_messages

COMPLAINT_CATEGORIES = constants.COMPLAINT_CATEGORIES
COMPLAINT_URGENCIES = constants.COMPLAINT_URGENCIES


def build_text_pipeline():
    return Pipeline([
        ("clean", FunctionTransformer(clean_messages, validate=False)),
        ("vectorize", TfidfVectorizer(
            ngram_range=(1, 2), min_df=constants.TEXT_MINIMUM_DOCUMENT_COUNT,
            max_features=constants.TEXT_MAXIMUM_FEATURES,
        )),
        ("decide", LogisticRegression(max_iter=1000, random_state=constants.MODEL_SEED)),
    ])


def split_complaints(corpus, label_column):
    messages = corpus["message_text"]
    labels = corpus[label_column]
    return train_test_split(
        messages, labels, test_size=constants.HELD_OUT_SHARE,
        random_state=constants.MODEL_SEED, stratify=labels,
    )


def train_category_classifier(fitting_text, fitting_labels):
    model = build_text_pipeline()
    model.fit(fitting_text, fitting_labels)
    return model


def train_urgency_classifier(fitting_text, fitting_labels):
    model = build_text_pipeline()
    model.fit(fitting_text, fitting_labels)
    return model


def classify_message(category_model, urgency_model, message):
    category = category_model.predict([message])[0]
    urgency = urgency_model.predict([message])[0]
    return {"category": category, "urgency": urgency}


if __name__ == "__main__":
    import joblib

    corpus = pd.read_csv(constants.COMPLAINT_MESSAGES_PATH)

    category_fitting_text, category_held_out_text, category_fitting_labels, \
        category_held_out_labels = split_complaints(corpus, "category")
    category_model = train_category_classifier(category_fitting_text, category_fitting_labels)
    category_score = category_model.score(category_held_out_text, category_held_out_labels)

    urgency_fitting_text, urgency_held_out_text, urgency_fitting_labels, \
        urgency_held_out_labels = split_complaints(corpus, "urgency")
    urgency_model = train_urgency_classifier(urgency_fitting_text, urgency_fitting_labels)
    urgency_score = urgency_model.score(urgency_held_out_text, urgency_held_out_labels)

    Path(constants.COMPLAINT_CATEGORY_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(category_model, constants.COMPLAINT_CATEGORY_MODEL_PATH)
    joblib.dump(urgency_model, constants.COMPLAINT_URGENCY_MODEL_PATH)

    scores = {"category": round(category_score, 4), "urgency": round(urgency_score, 4)}
    Path(constants.COMPLAINT_SCORES_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(constants.COMPLAINT_SCORES_PATH).write_text(json.dumps(scores, indent=2))

    print(scores)
