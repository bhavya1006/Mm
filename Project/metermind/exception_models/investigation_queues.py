"""Sorts classified readings into the five queues the company actually works."""

from pathlib import Path

import pandas as pd

from config import constants

QUEUE_BY_DECISION = dict(constants.QUEUE_FILE_PATHS)
QUEUES = tuple(QUEUE_BY_DECISION)


def sort_into_queues(book, decided):
    labelled = book.copy()
    labelled["_decided_class"] = list(decided)

    sorted_out = {}
    for queue_name in QUEUES:
        rows = labelled[labelled["_decided_class"] == queue_name].drop(columns=["_decided_class"])
        sorted_out[queue_name] = rows.reset_index(drop=True)
    return sorted_out


def queue_counts(sorted_out):
    return {name: len(rows) for name, rows in sorted_out.items()}


def write_queue_files(sorted_out, paths=None):
    paths_to_use = paths if paths is not None else QUEUE_BY_DECISION

    written = {}
    for name, rows in sorted_out.items():
        path = Path(paths_to_use[name])
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(path, index=False)
        written[name] = path
    return written


if __name__ == "__main__":
    from metermind.exception_models.baseline_model import load_model, predict_exception
    from metermind.exception_models.champion_model import predict_with_rule
    from metermind.exception_models.feature_engineering import widen_readings
    import json

    waiting = widen_readings(pd.read_csv(constants.READING_BOOK_PREDICT_PATH))
    champion = load_model(constants.CHAMPION_MODEL_PATH)
    rule = json.loads(Path(constants.OPERATING_RULE_PATH).read_text())

    from metermind.exception_models.feature_pipeline import modelling_columns
    decided = predict_with_rule(champion, waiting[list(modelling_columns(True))],
                                rule["tamper_floor"], rule["fault_floor"])

    sorted_out = sort_into_queues(waiting, decided)
    write_queue_files(sorted_out)
    print(queue_counts(sorted_out))
