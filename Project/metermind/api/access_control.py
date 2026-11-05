"""Who is calling, what they may do, and a written record of every case moved."""

import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from config import constants

AUDIT_TRAIL_FIELDS = ("recorded_at", "actor", "role", "reading_id", "from_status", "to_status")

bearer_scheme = HTTPBearer(auto_error=False)


def read_signing_secret():
    return os.environ.get(constants.TOKEN_SECRET_ENVIRONMENT_NAME) or constants.DEVELOPMENT_SECRET


def issue_token(subject, role):
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=constants.TOKEN_VALID_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expires_at}
    return jwt.encode(payload, read_signing_secret(), algorithm="HS256")


def read_token(token):
    try:
        return jwt.decode(token, read_signing_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="the token could not be read")


def require_inspector(carried: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if carried is None:
        raise HTTPException(status_code=401, detail="the token could not be read")
    payload = read_token(carried.credentials)
    if payload.get("role") != constants.INSPECTOR_ROLE:
        raise HTTPException(
            status_code=403, detail=f"the role {constants.INSPECTOR_ROLE} is required"
        )
    return payload


def require_signed_in(carried: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if carried is None:
        raise HTTPException(status_code=401, detail="the token could not be read")
    return read_token(carried.credentials)


def record_audit_entry(actor, role, reading_identifier, from_status, to_status,
                        trail_path=constants.AUDIT_TRAIL_PATH):
    trail_path = Path(trail_path)
    trail_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not trail_path.exists()

    with open(trail_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(AUDIT_TRAIL_FIELDS)
        writer.writerow((
            datetime.now(timezone.utc).isoformat(), actor, role, reading_identifier,
            from_status, to_status,
        ))

    return trail_path


if __name__ == "__main__":
    issued = issue_token("je/1180", constants.INSPECTOR_ROLE)
    print(f"issued: {issued}")
    print(f"reads back as: {read_token(issued)}")
