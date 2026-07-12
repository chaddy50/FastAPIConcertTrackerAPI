"""Auth-required + custom-row owner-scoping for the reference catalog.

Externally-sourced rows (with a natural key) stay shared/global; rows a user
hand-enters (no natural key) are private to their creator.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.composer import Composer
from app.models.performer import Performer
from app.models.venue import Venue
from app.models.work import Work

# (list path, a minimal custom-create body, a minimal global-create body)
CATALOGS = {
    "venues": (
        "/v1/venues/",
        {"name": "My Living Room"},
        {"name": "Carnegie Hall", "osm_type": "way", "osm_id": 42},
    ),
    "performers": (
        "/v1/performers/",
        {"name": "My Garage Band", "type": "ENSEMBLE"},
        {"name": "Berlin Phil", "type": "ORCHESTRA", "musicbrainz_id": "mb-1"},
    ),
    "composers": (
        "/v1/composers/",
        {"name": "My Uncle Steve"},
        {"name": "J.S. Bach", "open_opus_id": "oo-1"},
    ),
    "works": (
        "/v1/works/",
        {"title": "My Improvisation", "composers": [{"name": "Me"}]},
        {"title": "Mass in B Minor", "open_opus_id": "oo-w-1", "composers": [{"name": "Bach"}]},
    ),
}

CATALOG_NAMES = list(CATALOGS.keys())


# --- require-auth (401 without a key) -------------------------------------


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_catalog_list_requires_auth(unauth_client: TestClient, name):
    path, _, _ = CATALOGS[name]
    assert unauth_client.get(path).status_code == 401


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_catalog_get_by_id_requires_auth(unauth_client: TestClient, name):
    path, _, _ = CATALOGS[name]
    assert unauth_client.get(f"{path}some-id").status_code == 401


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_catalog_create_requires_auth(unauth_client: TestClient, name):
    path, custom_body, _ = CATALOGS[name]
    assert unauth_client.post(path, json=custom_body).status_code == 401


def test_venue_patch_and_delete_require_auth(unauth_client: TestClient):
    assert unauth_client.patch("/v1/venues/some-id", json={"name": "x"}).status_code == 401
    assert unauth_client.delete("/v1/venues/some-id").status_code == 401


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_catalog_unknown_key_401(unauth_client: TestClient, name):
    path, _, _ = CATALOGS[name]
    response = unauth_client.get(path, headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


# --- custom rows are owner-scoped -----------------------------------------


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_custom_row_visible_to_owner(client: TestClient, name):
    path, custom_body, _ = CATALOGS[name]
    created = client.post(path, json=custom_body).json()
    ids = {row["id"] for row in client.get(path).json()}
    assert created["id"] in ids


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_custom_row_hidden_from_other_user(client: TestClient, other_client: TestClient, name):
    path, custom_body, _ = CATALOGS[name]
    created = client.post(path, json=custom_body).json()
    ids = {row["id"] for row in other_client.get(path).json()}
    assert created["id"] not in ids


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_custom_row_get_by_id_cross_user_404(
    client: TestClient, other_client: TestClient, name
):
    path, custom_body, _ = CATALOGS[name]
    created = client.post(path, json=custom_body).json()
    assert other_client.get(f"{path}{created['id']}").status_code == 404


def test_custom_row_stamps_owner_global_row_does_not(
    client: TestClient, db_session: Session, user
):
    custom = client.post("/v1/performers/", json={"name": "Custom", "type": "ENSEMBLE"}).json()
    glob = client.post(
        "/v1/performers/", json={"name": "Global", "type": "ORCHESTRA", "musicbrainz_id": "mb-x"}
    ).json()
    assert db_session.get(Performer, custom["id"]).user_id == user.id
    assert db_session.get(Performer, glob["id"]).user_id is None


def test_two_users_same_name_custom_rows_are_distinct(
    client: TestClient, other_client: TestClient
):
    a = client.post("/v1/composers/", json={"name": "Same Name"}).json()
    b = other_client.post("/v1/composers/", json={"name": "Same Name"}).json()
    assert a["id"] != b["id"]
    # each visible only to its owner
    assert {r["id"] for r in client.get("/v1/composers/").json()} == {a["id"]}
    assert {r["id"] for r in other_client.get("/v1/composers/").json()} == {b["id"]}


def test_name_filter_returns_own_custom_and_global_not_others(
    client: TestClient, other_client: TestClient
):
    glob = client.post(
        "/v1/performers/", json={"name": "Shared Orchestra", "type": "ORCHESTRA", "musicbrainz_id": "mb-shared"}
    ).json()
    mine = client.post("/v1/performers/", json={"name": "Shared Ensemble", "type": "ENSEMBLE"}).json()
    theirs = other_client.post(
        "/v1/performers/", json={"name": "Shared Quartet", "type": "ENSEMBLE"}
    ).json()

    ids = {r["id"] for r in client.get("/v1/performers/?name=Shared").json()}
    assert glob["id"] in ids
    assert mine["id"] in ids
    assert theirs["id"] not in ids


# --- shared global rows ----------------------------------------------------


def test_global_row_visible_across_users(client: TestClient, other_client: TestClient):
    created = client.post(
        "/v1/performers/", json={"name": "Vienna Phil", "type": "ORCHESTRA", "musicbrainz_id": "mb-vienna"}
    ).json()
    ids = {r["id"] for r in other_client.get("/v1/performers/").json()}
    assert created["id"] in ids


def test_global_row_dedup_across_users_same_row(client: TestClient, other_client: TestClient):
    a = client.post(
        "/v1/composers/", json={"name": "Mozart", "open_opus_id": "oo-mozart"}
    ).json()
    b = other_client.post(
        "/v1/composers/", json={"name": "Mozart", "open_opus_id": "oo-mozart"}
    ).json()
    assert a["id"] == b["id"]


def test_global_venue_mutable_by_any_user(client: TestClient, other_client: TestClient):
    venue = client.post(
        "/v1/venues/", json={"name": "Shared Hall", "osm_type": "way", "osm_id": 777}
    ).json()
    # other user (who did not create it) can still PATCH the global row
    response = other_client.patch(f"/v1/venues/{venue['id']}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_cross_user_custom_venue_patch_delete_404(
    client: TestClient, other_client: TestClient, db_session: Session
):
    venue = client.post("/v1/venues/", json={"name": "Private Studio"}).json()
    assert other_client.patch(f"/v1/venues/{venue['id']}", json={"name": "x"}).status_code == 404
    assert other_client.delete(f"/v1/venues/{venue['id']}").status_code == 404
    # untouched
    assert db_session.get(Venue, venue["id"]).name == "Private Studio"


def test_custom_work_custom_composer_shares_owner(
    client: TestClient, db_session: Session, user
):
    work = client.post(
        "/v1/works/", json={"title": "My Sonata", "composers": [{"name": "My Teacher"}]}
    ).json()
    persisted = db_session.get(Work, work["id"])
    assert persisted.user_id == user.id
    assert persisted.composers[0].user_id == user.id


def test_custom_work_global_composer_stays_ownerless(
    client: TestClient, db_session: Session, user
):
    work = client.post(
        "/v1/works/",
        json={
            "title": "My Arrangement",
            "composers": [{"name": "Beethoven", "open_opus_id": "oo-beethoven"}],
        },
    ).json()
    persisted = db_session.get(Work, work["id"])
    assert persisted.user_id == user.id  # the work itself is custom
    assert persisted.composers[0].user_id is None  # but its composer is global
