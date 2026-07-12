import hashlib
import string

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.auth import generate_api_key, hash_api_key

# --- security primitives (unit) -------------------------------------------


def test_hash_api_key_matches_sha256():
    assert hash_api_key("hello") == hashlib.sha256(b"hello").hexdigest()


def test_hash_api_key_is_deterministic():
    assert hash_api_key("abc") == hash_api_key("abc")


def test_hash_api_key_distinct_inputs_distinct_hashes():
    assert hash_api_key("abc") != hash_api_key("abd")


def test_hash_api_key_never_returns_plaintext():
    assert hash_api_key("secret") != "secret"


def test_generate_api_key_non_empty():
    assert generate_api_key()


def test_generate_api_key_unique():
    assert generate_api_key() != generate_api_key()


def test_generate_api_key_is_url_safe():
    allowed = set(string.ascii_letters + string.digits + "-_")
    assert set(generate_api_key()) <= allowed


def test_generate_api_key_has_entropy():
    assert len(generate_api_key()) >= 40


# --- get_current_user (via GET /auth/me) ----------------------------------


def test_me_missing_header_401(unauth_client: TestClient):
    assert unauth_client.get("/v1/auth/me").status_code == 401


def test_me_malformed_header_401(unauth_client: TestClient):
    response = unauth_client.get("/v1/auth/me", headers={"Authorization": "Basic abc"})
    assert response.status_code == 401


def test_me_empty_bearer_token_401(unauth_client: TestClient):
    response = unauth_client.get("/v1/auth/me", headers={"Authorization": "Bearer "})
    assert response.status_code == 401


def test_me_unknown_key_401(unauth_client: TestClient):
    response = unauth_client.get(
        "/v1/auth/me", headers={"Authorization": "Bearer totally-unknown-key"}
    )
    assert response.status_code == 401


def test_me_401_body_does_not_echo_key(unauth_client: TestClient):
    response = unauth_client.get(
        "/v1/auth/me", headers={"Authorization": "Bearer super-secret-guess"}
    )
    assert "super-secret-guess" not in response.text


def test_me_valid_key_returns_caller(client: TestClient, user: User):
    response = client.get("/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] == user.username


def test_me_never_leaks_key_or_hash(client: TestClient):
    data = client.get("/v1/auth/me").json()
    assert "api_key" not in data
    assert "api_key_hash" not in data


# --- POST /auth/register --------------------------------------------------


def test_register_returns_key_id_username(unauth_client: TestClient):
    response = unauth_client.post("/v1/auth/register", json={"username": "alice"})
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice"
    assert data["api_key"]
    assert data["id"]


def test_register_is_unauthenticated(unauth_client: TestClient):
    # No Authorization header required to create the first account.
    assert unauth_client.post("/v1/auth/register", json={"username": "bob"}).status_code == 201


def test_register_key_authenticates(unauth_client: TestClient):
    key = unauth_client.post("/v1/auth/register", json={"username": "carol"}).json()["api_key"]
    response = unauth_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {key}"})
    assert response.status_code == 200
    assert response.json()["username"] == "carol"


def test_register_persists_hash_not_plaintext(unauth_client: TestClient, db_session: Session):
    key = unauth_client.post("/v1/auth/register", json={"username": "dave"}).json()["api_key"]
    user = db_session.query(User).where(User.username == "dave").first()
    assert user is not None
    assert user.api_key_hash == hash_api_key(key)
    assert key not in user.api_key_hash


def test_register_blank_username_422(unauth_client: TestClient):
    assert unauth_client.post("/v1/auth/register", json={"username": "   "}).status_code == 422


def test_register_duplicate_username_409(unauth_client: TestClient):
    unauth_client.post("/v1/auth/register", json={"username": "eve"})
    assert unauth_client.post("/v1/auth/register", json={"username": "eve"}).status_code == 409


def test_register_trims_username(unauth_client: TestClient, db_session: Session):
    unauth_client.post("/v1/auth/register", json={"username": "  frank  "})
    assert db_session.query(User).where(User.username == "frank").first() is not None


def test_register_distinct_users_distinct_keys(unauth_client: TestClient):
    a = unauth_client.post("/v1/auth/register", json={"username": "grace"}).json()
    b = unauth_client.post("/v1/auth/register", json={"username": "heidi"}).json()
    assert a["id"] != b["id"]
    assert a["api_key"] != b["api_key"]


def test_register_populates_created_at(unauth_client: TestClient, db_session: Session):
    unauth_client.post("/v1/auth/register", json={"username": "ivan"})
    user = db_session.query(User).where(User.username == "ivan").first()
    assert user.created_at is not None
