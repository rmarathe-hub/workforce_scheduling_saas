import uuid

from fastapi.testclient import TestClient

from tests.helpers import cleanup_user


def test_register_creates_org_and_owner_membership(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/organizations/me", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["role"] == "OWNER"
    assert data[0]["organization"]["name"]


def test_get_organizations_me_returns_role(
    client: TestClient, registered_user: dict[str, str], auth_headers: dict[str, str]
) -> None:
    response = client.get("/organizations/me", headers=auth_headers)

    assert response.status_code == 200
    memberships = response.json()
    assert len(memberships) == 1
    assert memberships[0]["role"] == "OWNER"
    assert memberships[0]["organization"]["name"] == registered_user["organization_name"]


def test_create_additional_organization(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/organizations",
        headers=auth_headers,
        json={"name": "Second Org", "timezone": "America/Los_Angeles"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Second Org"
    assert response.json()["timezone"] == "America/Los_Angeles"

    list_response = client.get("/organizations/me", headers=auth_headers)
    assert len(list_response.json()) == 2


def test_non_member_cannot_access_organization(
    client: TestClient, db, auth_headers: dict[str, str]
) -> None:
    org_id = client.get("/organizations/me", headers=auth_headers).json()[0]["organization"]["id"]

    other_email = f"other-{uuid.uuid4()}@example.com"
    register_response = client.post(
        "/auth/register",
        json={
            "email": other_email,
            "password": "password123",
            "full_name": "Other User",
            "organization_name": f"Other Org {uuid.uuid4()}",
        },
    )
    other_user_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        json={"email": other_email, "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.get(f"/organizations/{org_id}", headers=other_headers)
    assert response.status_code == 403

    cleanup_user(db, other_user_id)
