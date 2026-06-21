from fastapi.testclient import TestClient


def test_register_succeeds(client: TestClient, db) -> None:
    import uuid

    email = f"register-{uuid.uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "New User",
            "organization_name": f"Org {uuid.uuid4()}",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == "New User"
    assert data["is_active"] is True
    assert "id" in data

    from tests.helpers import cleanup_user

    cleanup_user(db, data["id"])


def test_login_returns_token(client: TestClient, registered_user: dict[str, str]) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_me_with_valid_token(client: TestClient, registered_user: dict[str, str]) -> None:
    login_response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]
    assert response.json()["id"] == registered_user["id"]


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_login_with_wrong_password_returns_401(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "wrongpassword"},
    )

    assert response.status_code == 401
