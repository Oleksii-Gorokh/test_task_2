# Expedition Management Service

A backend service built with FastAPI, SQLite (SQLAlchemy + aiosqlite), and WebSockets to manage expeditions.

## Features

- JWT-based authentication and user roles (`chief` and `member`).
- Expedition lifecycle: `draft` -> `ready` -> `active` -> `finished`.
- Member invitations (invite/confirm) with capacity and conflicts verification.
- Real-time WebSocket notifications of member invitations, confirmations, and expedition status changes.
- Automated tests using pytest.
- Docker integration.

---

## Setup & Running

### Option 1: Run Locally

1. Install Python 3.12+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Access API documentation at `http://127.0.0.1:8000/docs`

### Option 2: Run with Docker Compose

1. Build and run containers:
   ```bash
   docker-compose up --build
   ```
2. The service is available at `http://localhost:8000`

---

## Running Tests

Run the test suite with pytest:
```bash
pytest
```

---

## API Documentation

### Auth API

- `POST /auth/register`: Create a new user with role `chief` or `member`.
- `POST /auth/login`: Authenticate and receive a JWT token.

### Expeditions API

- `POST /expeditions`: Create a new expedition in `draft` status (chief only).
- `GET /expeditions`: List the user's active expeditions.
- `POST /expeditions/{id}/ready`: Transition status to `ready` (chief only).
- `POST /expeditions/{id}/active`: Transition status to `active` (chief only). Checks start time, capacity, and active participants conflicts.
- `POST /expeditions/{id}/finish`: Transition status to `finished` (chief only).

### Members API

- `POST /expeditions/{expedition_id}/invite`: Invite a `member` to the expedition (chief only).
- `POST /members/{id}/confirm`: Confirm an invitation (member only).

---

## WebSockets

Real-time events are broadcast to authorized users involved in the expedition.

### Connection
Connect to:
`ws://localhost:8000/ws?token=<JWT_TOKEN>`

### Events Format
Clients receive events in the following JSON format:
```json
{
  "event": "member_invited" | "member_confirmed" | "expedition_status",
  "expedition_id": 1,
  "data": {}
}
```
