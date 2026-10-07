"""Account creation, login, and session tokens backed by the users table."""

import hashlib
import hmac
import os
import secrets
import sqlite3
from typing import Callable

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, Header, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# Argon2id with argon2-cffi's defaults (memory-hard, per-hash random salt).
hasher = PasswordHasher()

# Seed users in the provided DB use "pbkdf2_sha256$<salt>$<hex digest>" with 120k iterations.
LEGACY_PREFIX = "pbkdf2_sha256$"
LEGACY_ITERATIONS = 120_000

TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
# Set SESSION_SECRET in .env to keep sessions valid across restarts.
serializer = URLSafeTimedSerializer(os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32), salt="cc-session")

# Used to spend the same time verifying when the email doesn't exist (avoids user enumeration by timing).
_DUMMY_HASH = hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith(LEGACY_PREFIX):
        try:
            _, salt, digest = stored.split("$")
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), LEGACY_ITERATIONS).hex()
        return hmac.compare_digest(candidate, digest)
    try:
        return hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    return stored.startswith(LEGACY_PREFIX) or hasher.check_needs_rehash(stored)


class SignupIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupIn":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def public_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "name": row["name"],
        "email": row["email"],
    }


def session_response(row: sqlite3.Row) -> dict:
    return {"token": serializer.dumps({"uid": row["id"]}), "user": public_user(row)}


def make_router(get_db: Callable[[], sqlite3.Connection]) -> tuple[APIRouter, Callable, Callable]:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def current_user(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
        try:
            data = serializer.loads(authorization[7:], max_age=TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again")
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (data.get("uid"),)).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found")
        return public_user(row)

    def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
        """Like current_user, but anonymous shoppers (or stale tokens) get None instead of a 401."""
        if not authorization:
            return None
        try:
            return current_user(authorization)
        except HTTPException:
            return None

    @router.post("/signup", status_code=status.HTTP_201_CREATED)
    def signup(body: SignupIn) -> dict:
        email = body.email.lower()
        with get_db() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                    (f"{body.first_name} {body.last_name}", email, hash_password(body.password),
                     body.first_name, body.last_name),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists")
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return session_response(row)

    @router.post("/login")
    def login(body: LoginIn) -> dict:
        email = body.email.lower()
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
            if row is None:
                verify_password(body.password, _DUMMY_HASH)
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
            if not verify_password(body.password, row["password_hash"]):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
            # Transparently upgrade legacy PBKDF2 hashes to Argon2id on successful login.
            if needs_rehash(row["password_hash"]):
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["id"]))
        return session_response(row)

    @router.get("/me")
    def me(user: dict = Depends(current_user)) -> dict:
        return {"user": user}

    return router, current_user, optional_user
