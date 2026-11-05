"""The router, its store, and every route the reading book answers."""

from fastapi import APIRouter, Depends, HTTPException, Query

from config import constants
from metermind.api import schemas
from metermind.api.access_control import record_audit_entry, require_inspector, require_signed_in
from metermind.api.case_transitions import move_case_status
from metermind.api.repository import InMemoryReadingRepository
from metermind.core.entities import create_service_connection
from metermind.core.exceptions import MeterMindError, ReadingStorageError, UnsupportedCategoryError

router = APIRouter(tags=["readings"])
reading_repository = InMemoryReadingRepository()


def price_reading(stored_reading):
    connection = create_service_connection(stored_reading)
    return schemas.ReadingReply(
        reading_id=stored_reading["reading_id"],
        account_number=connection.account_number,
        consumer_category=connection.consumer_category,
        units_consumed=round(connection.units_consumed, 1),
        energy_charge_inr=round(connection.energy_charge_inr(), 2),
        fixed_charge_inr=round(connection.fixed_charge_inr(), 2),
        net_bill_inr=round(connection.net_bill_inr(), 2),
        is_billable=connection.is_billable(),
        refusal_reasons=connection.refusal_reasons(),
    )


@router.post("/readings", response_model=schemas.ReadingReply, status_code=201)
def submit_reading(submitted_reading: schemas.ReadingSubmission):
    reading = submitted_reading.model_dump()
    try:
        create_service_connection(reading)
    except UnsupportedCategoryError as refused:
        raise HTTPException(status_code=422, detail=str(refused))

    stored = reading_repository.add_reading(reading)
    return price_reading(stored)


@router.get("/readings/{reading_identifier}", response_model=schemas.ReadingReply)
def read_reading(reading_identifier: str):
    try:
        stored = reading_repository.get_reading(reading_identifier)
    except ReadingStorageError as refused:
        raise HTTPException(status_code=404, detail=str(refused))
    return price_reading(stored)


@router.put("/readings/{reading_identifier}", response_model=schemas.ReadingReply)
def replace_reading(reading_identifier: str, submitted_reading: schemas.ReadingSubmission):
    reading = submitted_reading.model_dump()
    try:
        create_service_connection(reading)
    except UnsupportedCategoryError as refused:
        raise HTTPException(status_code=422, detail=str(refused))

    try:
        stored = reading_repository.replace_reading(reading_identifier, reading)
    except ReadingStorageError as refused:
        raise HTTPException(status_code=404, detail=str(refused))
    return price_reading(stored)


@router.delete("/readings/{reading_identifier}", status_code=204)
def remove_reading(reading_identifier: str):
    try:
        reading_repository.remove_reading(reading_identifier)
    except ReadingStorageError as refused:
        raise HTTPException(status_code=404, detail=str(refused))


@router.patch("/readings/{reading_identifier}/status", response_model=schemas.CaseStatusReply)
def change_case_status(reading_identifier: str, wanted: schemas.CaseStatusRequest,
                        carried=Depends(require_inspector)):
    try:
        stored = reading_repository.get_reading(reading_identifier)
    except ReadingStorageError as refused:
        raise HTTPException(status_code=404, detail=str(refused))

    current_status = stored.get("case_status") or constants.INITIAL_CASE_STATUS
    try:
        new_status = move_case_status(current_status, wanted.wanted_status)
    except MeterMindError as refused:
        raise HTTPException(status_code=409, detail=str(refused))

    stored["case_status"] = new_status
    reading_repository.replace_reading(reading_identifier, stored)

    record_audit_entry(wanted.noted_by, carried.get("role"), reading_identifier,
                       current_status, new_status)

    return schemas.CaseStatusReply(reading_id=reading_identifier, from_status=current_status,
                                   to_status=new_status, recorded_by=wanted.noted_by)


@router.get("/readings", response_model=schemas.PagedReadings)
def list_readings(consumer_category: str = Query(default=None),
                   read_type: str = Query(default=None),
                   page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=20, ge=1, le=200),
                   carried=Depends(require_signed_in)):
    matched = reading_repository.list_readings()
    if consumer_category:
        matched = [one for one in matched if one.get("consumer_category") == consumer_category]
    if read_type:
        matched = [one for one in matched if one.get("read_type") == read_type]

    total = len(matched)
    start = (page - 1) * page_size
    page_rows = matched[start:start + page_size]

    return schemas.PagedReadings(
        readings=[price_reading(one) for one in page_rows],
        page=page, page_size=page_size, total=total,
    )
