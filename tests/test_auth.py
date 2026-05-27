import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    response = await client.post("/auth/register", json={
        "email": "chief1@example.com",
        "password": "securepassword",
        "name": "Chief One",
        "role": "chief"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "chief1@example.com"
    assert response.json()["role"] == "chief"

    response = await client.post("/auth/register", json={
        "email": "chief1@example.com",
        "password": "securepassword",
        "name": "Chief One",
        "role": "chief"
    })
    assert response.status_code == 400

    response = await client.post("/auth/register", json={
        "email": "member1@example.com",
        "password": "securepassword",
        "name": "Member One",
        "role": "invalid_role"
    })
    assert response.status_code == 422

    response = await client.post("/auth/login", data={
        "username": "chief1@example.com",
        "password": "securepassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

    response = await client.post("/auth/login", data={
        "username": "chief1@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
