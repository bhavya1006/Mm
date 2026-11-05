"""Password hashing. What is stored never contains the password."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

hasher = PasswordHasher()


def hash_password(plain_password):
    return hasher.hash(plain_password)


def verify_password(plain_password, hashed_password):
    try:
        return hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash, VerificationError):
        return False


if __name__ == "__main__":
    stored = hash_password("Chennai#2026")
    print(f"the stored hash begins: {stored[:29]}... and then a salt that differs every time")
    print(f"the right password verifies : {verify_password('Chennai#2026', stored)}")
    print(f"a different one does not    : {verify_password('SomethingElse#1', stored)}")
