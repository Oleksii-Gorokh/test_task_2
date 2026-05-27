from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient

async def create_user(client: AsyncClient, email: str, name: str, role: str) -> dict:
    response = await client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": name,
        "role": role
    })
    return response.json()

async def get_token(client: AsyncClient, email: str) -> str:
    response = await client.post("/auth/login", data={
        "username": email,
        "password": "password123"
    })
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_expedition_lifecycle(client: AsyncClient):
    chief = await create_user(client, "chief_l@example.com", "Chief L", "chief")
    member1 = await create_user(client, "member1_l@example.com", "Member 1", "member")
    member2 = await create_user(client, "member2_l@example.com", "Member 2", "member")

    chief_token = await get_token(client, "chief_l@example.com")
    m1_token = await get_token(client, "member1_l@example.com")
    m2_token = await get_token(client, "member2_l@example.com")

    headers_chief = {"Authorization": f"Bearer {chief_token}"}
    headers_m1 = {"Authorization": f"Bearer {m1_token}"}
    headers_m2 = {"Authorization": f"Bearer {m2_token}"}

    response = await client.post("/expeditions", headers=headers_chief, json={
        "title": "Expedition 1",
        "description": "First Expedition",
        "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)).isoformat(),
        "capacity": 2
    })
    assert response.status_code == 201
    exp_id = response.json()["id"]
    assert response.json()["status"] == "draft"

    response = await client.post(f"/expeditions/{exp_id}/invite", headers=headers_chief, json={"user_id": member1["id"]})
    assert response.status_code == 201
    invite1_id = response.json()["id"]

    response = await client.post(f"/expeditions/{exp_id}/invite", headers=headers_chief, json={"user_id": member1["id"]})
    assert response.status_code == 400

    response = await client.post(f"/expeditions/{exp_id}/invite", headers=headers_chief, json={"user_id": chief["id"]})
    assert response.status_code == 400

    response = await client.post(f"/expeditions/{exp_id}/invite", headers=headers_chief, json={"user_id": member2["id"]})
    assert response.status_code == 201
    invite2_id = response.json()["id"]

    response = await client.post(f"/members/{invite1_id}/confirm", headers=headers_m2)
    assert response.status_code == 403

    response = await client.post(f"/members/{invite1_id}/confirm", headers=headers_m1)
    assert response.status_code == 200
    assert response.json()["state"] == "confirmed"

    response = await client.post(f"/members/{invite1_id}/confirm", headers=headers_m1)
    assert response.status_code == 400

    response = await client.post(f"/expeditions/{exp_id}/active", headers=headers_chief)
    assert response.status_code == 400

    response = await client.post(f"/expeditions/{exp_id}/ready", headers=headers_chief)
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

    response = await client.post(f"/expeditions/{exp_id}/active", headers=headers_chief)
    assert response.status_code == 400

    response = await client.post(f"/members/{invite2_id}/confirm", headers=headers_m2)
    assert response.status_code == 200

    response = await client.post(f"/expeditions/{exp_id}/active", headers=headers_chief)
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    response = await client.post(f"/expeditions/{exp_id}/finish", headers=headers_chief)
    assert response.status_code == 200
    assert response.json()["status"] == "finished"

    response = await client.post(f"/expeditions/{exp_id}/active", headers=headers_chief)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_active_constraints(client: AsyncClient):
    chief = await create_user(client, "chief_c@example.com", "Chief C", "chief")
    m1 = await create_user(client, "m1_c@example.com", "M1", "member")
    m2 = await create_user(client, "m2_c@example.com", "M2", "member")
    m3 = await create_user(client, "m3_c@example.com", "M3", "member")

    chief_token = await get_token(client, "chief_c@example.com")
    m1_token = await get_token(client, "m1_c@example.com")
    m2_token = await get_token(client, "m2_c@example.com")
    m3_token = await get_token(client, "m3_c@example.com")

    headers_chief = {"Authorization": f"Bearer {chief_token}"}
    headers_m1 = {"Authorization": f"Bearer {m1_token}"}
    headers_m2 = {"Authorization": f"Bearer {m2_token}"}
    headers_m3 = {"Authorization": f"Bearer {m3_token}"}

    response = await client.post("/expeditions", headers=headers_chief, json={
        "title": "Future Expedition",
        "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)).isoformat(),
        "capacity": 2
    })
    future_exp_id = response.json()["id"]

    inv1 = await client.post(f"/expeditions/{future_exp_id}/invite", headers=headers_chief, json={"user_id": m1["id"]})
    inv2 = await client.post(f"/expeditions/{future_exp_id}/invite", headers=headers_chief, json={"user_id": m2["id"]})
    
    await client.post(f"/members/{inv1.json()['id']}/confirm", headers=headers_m1)
    await client.post(f"/members/{inv2.json()['id']}/confirm", headers=headers_m2)
    
    await client.post(f"/expeditions/{future_exp_id}/ready", headers=headers_chief)
    response = await client.post(f"/expeditions/{future_exp_id}/active", headers=headers_chief)
    assert response.status_code == 400

    response = await client.post("/expeditions", headers=headers_chief, json={
        "title": "Low Capacity",
        "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)).isoformat(),
        "capacity": 1
    })
    low_cap_id = response.json()["id"]

    inv1_low = await client.post(f"/expeditions/{low_cap_id}/invite", headers=headers_chief, json={"user_id": m1["id"]})
    inv2_low = await client.post(f"/expeditions/{low_cap_id}/invite", headers=headers_chief, json={"user_id": m2["id"]})
    
    await client.post(f"/members/{inv1_low.json()['id']}/confirm", headers=headers_m1)
    await client.post(f"/members/{inv2_low.json()['id']}/confirm", headers=headers_m2)
    
    await client.post(f"/expeditions/{low_cap_id}/ready", headers=headers_chief)
    response = await client.post(f"/expeditions/{low_cap_id}/active", headers=headers_chief)
    assert response.status_code == 400

    response = await client.post("/expeditions", headers=headers_chief, json={
        "title": "Expedition A",
        "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)).isoformat(),
        "capacity": 5
    })
    exp_a_id = response.json()["id"]
    inv1_a = await client.post(f"/expeditions/{exp_a_id}/invite", headers=headers_chief, json={"user_id": m1["id"]})
    inv2_a = await client.post(f"/expeditions/{exp_a_id}/invite", headers=headers_chief, json={"user_id": m2["id"]})
    await client.post(f"/members/{inv1_a.json()['id']}/confirm", headers=headers_m1)
    await client.post(f"/members/{inv2_a.json()['id']}/confirm", headers=headers_m2)
    await client.post(f"/expeditions/{exp_a_id}/ready", headers=headers_chief)
    res = await client.post(f"/expeditions/{exp_a_id}/active", headers=headers_chief)
    assert res.status_code == 200

    response = await client.post("/expeditions", headers=headers_chief, json={
        "title": "Expedition B",
        "start_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)).isoformat(),
        "capacity": 5
    })
    exp_b_id = response.json()["id"]
    inv1_b = await client.post(f"/expeditions/{exp_b_id}/invite", headers=headers_chief, json={"user_id": m1["id"]})
    inv3_b = await client.post(f"/expeditions/{exp_b_id}/invite", headers=headers_chief, json={"user_id": m3["id"]})
    await client.post(f"/members/{inv1_b.json()['id']}/confirm", headers=headers_m1)
    await client.post(f"/members/{inv3_b.json()['id']}/confirm", headers=headers_m3)
    await client.post(f"/expeditions/{exp_b_id}/ready", headers=headers_chief)
    res = await client.post(f"/expeditions/{exp_b_id}/active", headers=headers_chief)
    assert res.status_code == 400
