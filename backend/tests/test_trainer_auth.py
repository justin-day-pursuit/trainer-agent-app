"""
Trainer sign-in token tests.

Supabase signs tokens with ES256 on current projects. These tests use throwaway keys
and a stand-in for the key lookup, so they make no network calls.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.core import auth

CLAIMS = {"sub": "trainer-1", "aud": "authenticated", "exp": 4102444800}
PROJECT_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def stand_in_key_lookup(monkeypatch):
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=PROJECT_KEY.public_key())
    monkeypatch.setattr(auth, "_get_jwks_client", lambda: client)
    monkeypatch.setattr(auth.settings, "supabase_jwt_secret", "a-shared-secret-that-is-long-enough-for-hs256")


async def verify(token):
    return await auth.get_current_trainer(authorization=f"Bearer {token}")


async def test_accepts_a_token_signed_with_the_projects_key():
    token = jwt.encode(CLAIMS, PROJECT_KEY, algorithm="ES256")
    assert (await verify(token))["sub"] == "trainer-1"


async def test_still_accepts_shared_secret_tokens():
    token = jwt.encode(CLAIMS, auth.settings.supabase_jwt_secret, algorithm="HS256")
    assert (await verify(token))["sub"] == "trainer-1"


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode(CLAIMS, OTHER_KEY, algorithm="ES256"),
        jwt.encode({**CLAIMS, "aud": "someone-else"}, PROJECT_KEY, algorithm="ES256"),
        jwt.encode({**CLAIMS, "exp": 1}, PROJECT_KEY, algorithm="ES256"),
        jwt.encode(CLAIMS, "wrong-secret-that-is-long-enough-for-hs256-use", algorithm="HS256"),
        jwt.encode(CLAIMS, None, algorithm="none"),
        "not-a-token",
    ],
    ids=["wrong_key", "wrong_audience", "expired", "wrong_secret", "unsigned", "garbage"],
)
async def test_rejects_bad_tokens(token):
    with pytest.raises(HTTPException) as caught:
        await verify(token)
    assert caught.value.status_code == 401
