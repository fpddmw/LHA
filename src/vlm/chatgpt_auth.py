"""Official Sign in with ChatGPT credentials, separate from Codex sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN = ISSUER + "/api/accounts/oauth/token"
SCOPE = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
DEFAULT_CREDENTIAL_FILE = "~/.config/lha/chatgpt-subscription.json"


class AuthenticationError(RuntimeError):
    retryable = False


def credential_path(path=None):
    return Path(
        path or os.environ.get("LHA_CHATGPT_CREDENTIAL_FILE", DEFAULT_CREDENTIAL_FILE)
    ).expanduser()


def save_private(path, value):
    """Replace tokens together; temp files are owner-only from creation."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def token_request(fields):
    request = urllib.request.Request(
        TOKEN,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never include a token response or request in diagnostics.
        raise AuthenticationError(
            f"ChatGPT authorization failed (HTTP {exc.code}); sign in again"
        ) from None


def validate_identity(id_token, client_id, nonce=None):
    import jwt

    key = jwt.PyJWKClient(ISSUER + "/.well-known/jwks.json").get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=ISSUER,
        leeway=5,
        options={"require": ["sub", "exp", "iat"]},
    )
    if not isinstance(claims["sub"], str) or not claims["sub"]:
        raise AuthenticationError("ChatGPT returned no account identity")
    if nonce is not None and claims.get("nonce") != nonce:
        raise AuthenticationError("ChatGPT sign-in nonce did not match")
    return claims


def token_record(tokens, previous, *, nonce=None):
    record = dict(previous)
    if not tokens.get("access_token") or not tokens.get("refresh_token"):
        raise AuthenticationError("ChatGPT did not return a renewable session")
    scopes = tokens.get("scope", " ".join(record.get("scopes", []))).split()
    if "chatgpt.tokens.use.direct" not in scopes:
        raise AuthenticationError("ChatGPT plan usage was not granted")
    if tokens.get("token_type", "Bearer").lower() != "bearer":
        raise AuthenticationError("Unexpected ChatGPT token type")
    if nonce is not None or tokens.get("id_token"):
        claims = validate_identity(tokens.get("id_token", ""), record["client_id"], nonce)
        if record.get("subject") and claims["sub"] != record["subject"]:
            raise AuthenticationError("ChatGPT returned a different account")
        record.update(
            subject=claims["sub"],
            email=claims.get("email"),
            issuer=ISSUER,
            id_token=tokens["id_token"],
        )
    record.update(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        scopes=scopes,
        token_type="Bearer",
        saved_at=time.time(),
        expires_at=time.time() + float(tokens["expires_in"]),
        earliest_refresh_at=tokens.get("earliest_refresh_at"),
    )
    return record


def begin_sign_in(path, redirect_uri):
    path = credential_path(path)
    host_file = path.parent / "chatgpt-host.json"
    from planner_harness.lock import RunLock

    with RunLock(path.parent / "chatgpt-auth-lock", timeout=35):
        if not host_file.exists():
            save_private(host_file, {"ext_agent_host_id": "urn:uuid:" + str(uuid.uuid4())})
        host = json.loads(host_file.read_text())
    previous = json.loads(path.read_text()) if path.exists() else {}
    verifier, state, nonce = (
        secrets.token_urlsafe(64),
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
    )
    client_id = previous.get("client_id", "dynamic_agent_client")
    params = {
        "client_id": client_id,
        "ext_agent_host_id": host["ext_agent_host_id"],
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "resource": RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("="),
    }
    if client_id == "dynamic_agent_client":
        params["agent_name_hint"] = "LHA"
    pending = {
        "previous": previous,
        "client_id": client_id,
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
        "redirect_uri": redirect_uri,
        **host,
    }
    return AUTHORIZE + "?" + urllib.parse.urlencode(params), pending


def finish_sign_in(path, pending, query):
    values = urllib.parse.parse_qs(query)
    if values.get("state") != [pending["state"]]:
        raise AuthenticationError("Sign-in callback state did not match")
    if values.get("error"):
        raise AuthenticationError("ChatGPT sign-in was declined or unavailable")
    client_id = values.get("client_id", [pending["client_id"]])[0]
    if client_id == "dynamic_agent_client" or (
        pending["client_id"] != "dynamic_agent_client" and client_id != pending["client_id"]
    ):
        raise AuthenticationError("ChatGPT registration did not return the expected client ID")
    code = values.get("code", [None])[0]
    if not code:
        raise AuthenticationError("ChatGPT sign-in returned no authorization code")
    tokens = token_request(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": pending["verifier"],
            "redirect_uri": pending["redirect_uri"],
            "resource": RESOURCE,
        }
    )
    record = token_record(
        tokens,
        {
            **pending["previous"],
            "client_id": client_id,
            "ext_agent_host_id": pending["ext_agent_host_id"],
        },
        nonce=pending["nonce"],
    )
    save_private(credential_path(path), record)
    return {"status": "signed_in", "plan_usage_granted": True}


def access_token(path=None):
    from planner_harness.lock import RunLock

    path = credential_path(path)
    if not path.exists():
        raise AuthenticationError("Run scripts/chatgpt_subscription.py login to authorize LHA")
    with RunLock(path.parent / (path.stem + "-refresh-lock"), timeout=35):
        record = json.loads(path.read_text())
        if "chatgpt.tokens.use.direct" not in record.get("scopes", []):
            raise AuthenticationError("This session does not grant ChatGPT plan usage")
        if record["expires_at"] <= time.time() + 60:
            tokens = token_request(
                {
                    "grant_type": "refresh_token",
                    "client_id": record["client_id"],
                    "refresh_token": record["refresh_token"],
                    "resource": RESOURCE,
                }
            )
            record = token_record(tokens, record)
            save_private(path, record)
        return record["access_token"]


def credential_status(path=None):
    path = credential_path(path)
    if not path.exists():
        return {"configured": False, "plan_usage_granted": False}
    value = json.loads(path.read_text())
    return {
        "configured": bool(value.get("access_token")),
        "plan_usage_granted": "chatgpt.tokens.use.direct" in value.get("scopes", []),
        "expires_at": value.get("expires_at"),
        "renewable": bool(value.get("refresh_token")),
    }
