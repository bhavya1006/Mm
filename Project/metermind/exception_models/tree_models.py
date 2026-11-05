"""Two more families on the shared preparation, and what weighting the classes buys."""

from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from config import constants
from metermind.exception_models.feature_pipeline import build_feature_pipeline

EXCEPTION_CLASSES = constants.EXCEPTION_CLASSES


def build_decision_tree_model(class_weight=None, widened=False):
    return Pipeline([
        ("prepare", build_feature_pipeline(widened)),
        ("decide", DecisionTreeClassifier(
            max_depth=constants.DECISION_TREE_DEPTH_LIMIT, class_weight=class_weight,
            random_state=constants.MODEL_SEED,
        )),
    ])


def build_random_forest_model(class_weight=None, widened=False):
    return Pipeline([
        ("prepare", build_feature_pipeline(widened)),
        ("decide", RandomForestClassifier(
            n_estimators=constants.RANDOM_FOREST_TREE_COUNT,
            max_depth=constants.RANDOM_FOREST_DEPTH_LIMIT, class_weight=class_weight,
            random_state=constants.MODEL_SEED, n_jobs=1,
        )),
    ])


def train_decision_tree(fitting_columns, fitting_classes, class_weight=None):
    model = build_decision_tree_model(class_weight)
    model.fit(fitting_columns, fitting_classes)
    return model


def train_random_forest(fitting_columns, fitting_classes, class_weight=None):
    model = build_random_forest_model(class_weight)
    model.fit(fitting_columns, fitting_classes)
    return model


def compare_class_weighting(fitting_columns, held_out_columns, fitting_classes, held_out_classes):
    results = {}
    for label, class_weight in (("unweighted", None), ("balanced", "balanced")):
        model = train_random_forest(fitting_columns, fitting_classes, class_weight)
        predicted = model.predict(held_out_columns)
        recalls = recall_score(
            held_out_classes, predicted, labels=list(EXCEPTION_CLASSES), average=None,
            zero_division=0,
        )
        recall_by_class = dict(zip(EXCEPTION_CLASSES, (float(one) for one in recalls)))
        results[label] = {
            "recall_by_class": recall_by_class,
            "lowest_recall": min(recall_by_class.values()),
        }
    return results


if __name__ == "__main__":
    import pandas as pd
    from metermind.exception_models.baseline_model import split_readings

    book = pd.read_csv(constants.CLEAN_READING_BOOK_PATH)
    fitting_columns, held_out_columns, fitting_classes, held_out_classes = split_readings(book)

    tree = train_decision_tree(fitting_columns, fitting_classes)
    forest = train_random_forest(fitting_columns, fitting_classes)

    Path(constants.DECISION_TREE_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(constants.RANDOM_FOREST_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(tree, constants.DECISION_TREE_MODEL_PATH)
    joblib.dump(forest, constants.RANDOM_FOREST_MODEL_PATH)

    print(f"{constants.DECISION_TREE_MODEL_PATH} {round(tree.score(held_out_columns, held_out_classes), 4)}")
    print(f"{constants.RANDOM_FOREST_MODEL_PATH} {round(forest.score(held_out_columns, held_out_classes), 4)}")
