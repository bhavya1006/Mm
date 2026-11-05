"""The champion goes behind a route."""

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from config import constants
from metermind.api import schemas
from metermind.api.access_control import require_signed_in
from metermind.exception_models.baseline_model import load_model
from metermind.exception_models.champion_model import predict_with_rule
from metermind.exception_models.feature_engineering import widen_readings
from metermind.exception_models.feature_pipeline import modelling_columns
from metermind.exception_models.investigation_queues import QUEUE_BY_DECISION

router = APIRouter(tags=["screening"])

champion_model_path = constants.CHAMPION_MODEL_PATH
operating_rule_path = constants.OPERATING_RULE_PATH
loaded_champion = {}


def load_champion_once():
    if "model" not in loaded_champion:
        try:
            model = load_model(champion_model_path)
            rule = json.loads(Path(operating_rule_path).read_text())
        except (FileNotFoundError, OSError):
            raise HTTPException(
                status_code=503, detail="the champion model is not ready to answer yet"
            )
        loaded_champion["model"] = model
        loaded_champion["rule"] = rule
    return loaded_champion["model"], loaded_champion["rule"]


@router.post("/screening", response_model=schemas.ScreeningReply)
def screen_reading(submitted_reading: schemas.ScreeningRequest,
                    carried=Depends(require_signed_in)):
    model, rule = load_champion_once()

    row = pd.DataFrame([submitted_reading.model_dump()])
    widened = widen_readings(row)
    columns = list(modelling_columns(True))

    decided = predict_with_rule(model, widened[columns], rule["tamper_floor"], rule["fault_floor"])
    exception_class = decided[0]

    probabilities = model.predict_proba(widened[columns])[0]
    classes = list(model.classes_)
    confidence = float(probabilities[classes.index(exception_class)])

    return schemas.ScreeningReply(
        account_number=submitted_reading.account_number,
        billing_period=submitted_reading.billing_period,
        exception_class=exception_class,
        confidence=round(confidence, 4),
        goes_to=QUEUE_BY_DECISION[exception_class],
    )
