"""Accounts, sign-in, and the store they live in for as long as the service runs."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from config import constants
from metermind.api.access_control import issue_token
from metermind.api.password_hashing import hash_password, verify_password
from metermind.core import validators

router = APIRouter(tags=["accounts"])
accounts = {}


class AccountRequest(BaseModel):
    account_number: str
    email_address: str
    password: str
    role: str = constants.CONSUMER_ROLE

    @field_validator("account_number")
    @classmethod
    def account_number_is_well_formed(cls, given):
        if not validators.validate_account_number(given):
            raise ValueError("account_number must look like ACC10000000")
        return given.strip().upper()

    @field_validator("email_address")
    @classmethod
    def account_email_address_is_well_formed(cls, given):
        if not validators.validate_email_address(given):
            raise ValueError("email_address must be an address a reply could be sent to")
        return given.strip().lower()


class AccountReply(BaseModel):
    account_number: str
    email_address: str
    role: str


class LoginRequest(BaseModel):
    account_number: str
    password: str


class TokenReply(BaseModel):
    access_token: str
    token_type: str
    role: str


@router.post("/accounts", response_model=AccountReply, status_code=201)
def sign_up(wanted: AccountRequest):
    if wanted.account_number in accounts:
        raise HTTPException(status_code=409, detail="this account number has already signed up")

    accounts[wanted.account_number] = {
        "account_number": wanted.account_number,
        "email_address": wanted.email_address,
        "hashed_password": hash_password(wanted.password),
        "role": wanted.role,
    }
    return AccountReply(account_number=wanted.account_number, email_address=wanted.email_address,
                        role=wanted.role)


@router.post("/accounts/login", response_model=TokenReply)
def log_in(wanted: LoginRequest):
    held = accounts.get(wanted.account_number)
    if held is None or not verify_password(wanted.password, held["hashed_password"]):
        raise HTTPException(status_code=401, detail="the account number or password is wrong")

    token = issue_token(wanted.account_number, held["role"])
    return TokenReply(access_token=token, token_type="bearer", role=held["role"])
