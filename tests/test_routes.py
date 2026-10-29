import pytest
from sunday.dashboard.api.routes import create_or_verify_pairing

@pytest.mark.asyncio
async def test_create_or_verify_pairing_no_token():
    response = await create_or_verify_pairing(token=None)
    assert "pairing_token" in response
    assert response["pairing_token"].startswith("sun_pair_")
    assert response["expires_in"] == 3600
    assert "created_at" in response

@pytest.mark.asyncio
async def test_create_or_verify_pairing_empty_token():
    response = await create_or_verify_pairing(token="")
    assert "pairing_token" in response
    assert response["pairing_token"].startswith("sun_pair_")
    assert response["expires_in"] == 3600
    assert "created_at" in response

@pytest.mark.asyncio
async def test_create_or_verify_pairing_with_token():
    test_token = "sun_pair_12345"
    response = await create_or_verify_pairing(token=test_token)
    assert response == {"authenticated": True, "token": test_token}
