"""Not every mistake costs the same. The champion and its rule are chosen on cost."""

import json
from pathlib import Path

from config import constants

EXCEPTION_CLASSES = constants.EXCEPTION_CLASSES

COST_MATRIX = {
    "genuine_high_usage": {
        "genuine_high_usage": 0.0, "estimated_read": 1.0, "meter_fault": 1.0,
        "tamper_suspected": 10.0, "tariff_mismatch": 3.0,
    },
    "estimated_read": {
        "genuine_high_usage": 1.0, "estimated_read": 0.0, "meter_fault": 1.0,
        "tamper_suspected": 4.0, "tariff_mismatch": 2.0,
    },
    "meter_fault": {
        "genuine_high_usage": 1.0, "estimated_read": 1.0, "meter_fault": 0.0,
        "tamper_suspected": 4.0, "tariff_mismatch": 2.0,
    },
    "tamper_suspected": {
        "genuine_high_usage": 4.0, "estimated_read": 3.0, "meter_fault": 3.0,
        "tamper_suspected": 0.0, "tariff_mismatch": 3.0,
    },
    "tariff_mismatch": {
        "genuine_high_usage": 2.0, "estimated_read": 2.0, "meter_fault": 2.0,
        "tamper_suspected": 4.0, "tariff_mismatch": 0.0,
    },
}

TAMPER_FLOORS = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
FAULT_FLOORS = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6)

MODELS_THAT_REPORT_CONFIDENCE = ("baseline", "decision_tree", "random_forest")


def choose_champion(fitting_columns, fitting_classes, folds=None):
    from metermind.exception_models.cross_validation import cross_validate_models

    scored = cross_validate_models(fitting_columns, fitting_classes, folds)
    considered = {name: scores for name, scores in scored.items()
                 if name in MODELS_THAT_REPORT_CONFIDENCE}
    means = {name: sum(scores) / len(scores) for name, scores in considered.items()}
    winner = max(means, key=means.get)
    return winner, means


def expected_cost(truth, predicted):
    truth = list(truth)
    predicted = list(predicted)
    if len(truth) != len(predicted):
        raise ValueError("truth and predicted must be the same length")
    total = sum(COST_MATRIX[one_truth][one_predicted]
               for one_truth, one_predicted in zip(truth, predicted))
    return total / len(truth)


def predict_with_rule(model, columns, tamper_floor, fault_floor):
    probabilities = model.predict_proba(columns)
    classes = list(model.classes_)
    floor_by_class = {"tamper_suspected": tamper_floor, "tariff_mismatch": fault_floor}

    decided = []
    for row in probabilities:
        ranked = sorted(zip(classes, row), key=lambda pair: pair[1], reverse=True)
        chosen_class = ranked[0][0]
        for candidate_class, confidence in ranked:
            floor = floor_by_class.get(candidate_class)
            if floor is None or confidence >= floor:
                chosen_class = candidate_class
                break
        decided.append(chosen_class)

    return decided


def choose_operating_rule(model, held_out_columns, held_out_classes):
    best = None
    for tamper_floor in TAMPER_FLOORS:
        for fault_floor in FAULT_FLOORS:
            decided = predict_with_rule(model, held_out_columns, tamper_floor, fault_floor)
            cost = expected_cost(held_out_classes, decided)
            if best is None or cost < best["expected_cost"]:
                best = {
                    "tamper_floor": tamper_floor, "fault_floor": fault_floor,
                    "expected_cost": round(cost, constants.MEASUREMENT_DECIMAL_PLACES),
                }
    return best


def save_champion(model, rule, model_path, rule_path):
    from metermind.exception_models.baseline_model import save_model

    saved_model_path = save_model(model, model_path)

    rule_path = Path(rule_path)
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    rounded_rule = {
        key: (round(value, constants.MEASUREMENT_DECIMAL_PLACES)
             if isinstance(value, float) else value)
        for key, value in rule.items()
    }
    rule_path.write_text(json.dumps(rounded_rule, indent=2))

    return saved_model_path, rule_path


if __name__ == "__main__":
    import pandas as pd
    from metermind.exception_models.baseline_model import build_baseline_model, split_readings
    from metermind.exception_models.feature_engineering import widen_readings
    from metermind.exception_models.feature_pipeline import modelling_columns

    book = widen_readings(pd.read_csv(constants.CLEAN_READING_BOOK_PATH))
    fitting_columns, held_out_columns, fitting_classes, held_out_classes = split_readings(
        book, modelling_columns(True)
    )

    print(
        "only the families that report a confidence can carry an operating rule, so the "
        "support vector\nis not considered:"
    )
    chosen, means = choose_champion(fitting_columns, fitting_classes)
    print(f"chosen: {chosen} {means}")

    champion = build_baseline_model(widened=True) if chosen == "baseline" else None
    if chosen != "baseline":
        from metermind.exception_models.tree_models import (
            build_decision_tree_model,
            build_random_forest_model,
        )
        champion = (build_decision_tree_model(widened=True) if chosen == "decision_tree"
                   else build_random_forest_model(widened=True))
    champion.fit(fitting_columns, fitting_classes)

    argmax_predicted = champion.predict(held_out_columns)
    argmax_cost = expected_cost(held_out_classes, argmax_predicted)
    print(f"argmax cost: {round(argmax_cost, 4)}")

    rule = choose_operating_rule(champion, held_out_columns, held_out_classes)
    print(f"rule: {rule}")

    save_champion(champion, rule, constants.CHAMPION_MODEL_PATH, constants.OPERATING_RULE_PATH)
