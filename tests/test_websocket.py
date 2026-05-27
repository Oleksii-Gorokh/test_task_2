from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from tests.conftest import TestingSessionLocal

@pytest.mark.asyncio
async def test_websocket_notifications():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        
        response = client.post("/auth/register", json={
            "email": "chief_w@example.com",
            "password": "password123",
            "name": "Chief W",
            "role": "chief"
        })
        chief_id = response.json()["id"]
        
        response = client.post("/auth/register", json={
            "email": "member_w@example.com",
            "password": "password123",
            "name": "Member W",
            "role": "member"
        })
        member_id = response.json()["id"]

        token_chief = client.post("/auth/login", data={"username": "chief_w@example.com", "password": "password123"}).json()["access_token"]
        token_member = client.post("/auth/login", data={"username": "member_w@example.com", "password": "password123"}).json()["access_token"]

        headers_chief = {"Authorization": f"Bearer {token_chief}"}

        response = client.post("/expeditions", headers=headers_chief, json={
            "title": "WS Expedition",
            "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)).isoformat(),
            "capacity": 2
        })
        exp_id = response.json()["id"]

        with client.websocket_connect(f"/ws?token={token_chief}") as ws_chief:
            with client.websocket_connect(f"/ws?token={token_member}") as ws_member:
                
                response = client.post(f"/expeditions/{exp_id}/invite", headers=headers_chief, json={"user_id": member_id})
                invite_id = response.json()["id"]

                data_chief = ws_chief.receive_json()
                assert data_chief["event"] == "member_invited"
                assert data_chief["expedition_id"] == exp_id
                
                data_member = ws_member.receive_json()
                assert data_member["event"] == "member_invited"
                assert data_member["expedition_id"] == exp_id

                headers_member = {"Authorization": f"Bearer {token_member}"}
                client.post(f"/members/{invite_id}/confirm", headers=headers_member)

                data_chief = ws_chief.receive_json()
                assert data_chief["event"] == "member_confirmed"
                
                data_member = ws_member.receive_json()
                assert data_member["event"] == "member_confirmed"

                client.post(f"/expeditions/{exp_id}/ready", headers=headers_chief)
                
                data_chief = ws_chief.receive_json()
                assert data_chief["event"] == "expedition_status"
                assert data_chief["data"]["status"] == "ready"
    finally:
        app.dependency_overrides.clear()
