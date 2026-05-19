from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


class AdminAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdminIdentity:
    email: str
    display_name: str
    picture_url: str


@dataclass(frozen=True)
class AdminSession:
    email: str
    expires_at: int


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def verify_google_identity_token(credential: str, *, client_id: str) -> AdminIdentity:
    if not credential.strip():
        raise AdminAuthError("No se recibio una credencial de Google valida.")

    try:
        payload = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise AdminAuthError("No fue posible validar la identidad con Google.") from exc

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise AdminAuthError("La cuenta autenticada no incluye un correo valido.")
    if not payload.get("email_verified", False):
        raise AdminAuthError("La cuenta autenticada no tiene el correo verificado.")

    return AdminIdentity(
        email=email,
        display_name=str(payload.get("name", "")).strip(),
        picture_url=str(payload.get("picture", "")).strip(),
    )


def create_admin_session_token(email: str, *, secret: str, ttl_seconds: int) -> tuple[str, int]:
    expires_at = int(time.time()) + ttl_seconds
    payload = {
        "sub": email.strip().lower(),
        "exp": expires_at,
        "typ": "admin_session",
        "v": 1,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}", expires_at


def verify_admin_session_token(token: str, *, secret: str) -> AdminSession:
    if not token or "." not in token:
        raise AdminAuthError("La sesion administrativa es invalida.")

    payload_b64, signature_b64 = token.split(".", 1)
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature_b64, _b64url_encode(expected_signature)):
        raise AdminAuthError("La sesion administrativa no es valida.")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise AdminAuthError("La sesion administrativa no se pudo interpretar.") from exc

    if payload.get("typ") != "admin_session" or payload.get("v") != 1:
        raise AdminAuthError("La sesion administrativa tiene un formato no soportado.")

    email = str(payload.get("sub", "")).strip().lower()
    expires_at = int(payload.get("exp", 0) or 0)
    if not email or expires_at <= 0:
        raise AdminAuthError("La sesion administrativa esta incompleta.")
    if expires_at <= int(time.time()):
        raise AdminAuthError("La sesion administrativa ya expiro.")

    return AdminSession(email=email, expires_at=expires_at)
