"""Per-user scoping of performances and set-list entries: another user's rows
are invisible (404, never 403), user_id is stamped from the token, and every
endpoint requires a valid key.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.performance import Performance
from app.models.set_list_entry import SetListEntry
from tests.conftest import (
    OTHER_USER_ID,
    PRIMARY_USER_ID,
    _make_performance,
    _make_set_list_entry_row,
    _make_venue,
    _make_work,
)


def _perf_payload(venue_id: str, **extra) -> dict:
    return {"date": "2024-01-15T20:00:00+00:00", "status": "ATTENDED", "venue_id": venue_id, **extra}


# --- performances: isolation ----------------------------------------------


def test_list_returns_only_callers_rows(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    _make_performance(db_session, venue.id, user_id=PRIMARY_USER_ID)
    _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)

    data = client.get("/v1/performances/").json()
    assert len(data) == 1


def test_get_another_users_performance_404(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    theirs = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    assert client.get(f"/v1/performances/{theirs.id}").status_code == 404


def test_create_stamps_caller_as_owner(
    client: TestClient, db_session: Session, user
):
    venue = _make_venue(db_session)
    created = client.post("/v1/performances/", json=_perf_payload(venue.id)).json()
    assert db_session.get(Performance, created["id"]).user_id == user.id


def test_create_ignores_user_id_in_body(client: TestClient, db_session: Session, user):
    venue = _make_venue(db_session)
    created = client.post(
        "/v1/performances/", json=_perf_payload(venue.id, user_id=OTHER_USER_ID)
    ).json()
    assert db_session.get(Performance, created["id"]).user_id == user.id


def test_update_another_users_performance_404(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    theirs = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    response = client.put(f"/v1/performances/{theirs.id}", json={"status": "CANCELLED"})
    assert response.status_code == 404
    assert db_session.get(Performance, theirs.id).status.value == "ATTENDED"


def test_delete_another_users_performance_404_and_survives(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    theirs = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    assert client.delete(f"/v1/performances/{theirs.id}").status_code == 404
    assert db_session.get(Performance, theirs.id) is not None


def test_performances_require_auth(unauth_client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    assert unauth_client.get("/v1/performances/").status_code == 401
    assert unauth_client.get("/v1/performances/x").status_code == 401
    assert unauth_client.post("/v1/performances/", json=_perf_payload(venue.id)).status_code == 401
    assert unauth_client.put("/v1/performances/x", json={"status": "CANCELLED"}).status_code == 401
    assert unauth_client.delete("/v1/performances/x").status_code == 401


# --- set-list entries: isolation ------------------------------------------


def _entry_payload(performance_id: str, work_id: str, **extra) -> dict:
    return {
        "performance_id": performance_id,
        "work_id": work_id,
        "order": 1,
        "featured_performers": [],
        **extra,
    }


def test_create_entry_against_another_users_performance_404(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    theirs = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    response = client.post("/v1/set-list-entries/", json=_entry_payload(theirs.id, work.id))
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_created_entry_owned_by_caller(client: TestClient, db_session: Session, user):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    perf = _make_performance(db_session, venue.id, user_id=PRIMARY_USER_ID)
    created = client.post("/v1/set-list-entries/", json=_entry_payload(perf.id, work.id)).json()
    assert db_session.get(SetListEntry, created["id"]).user_id == user.id


def test_update_another_users_entry_404(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    perf = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    entry = _make_set_list_entry_row(db_session, perf.id, work.id, user_id=OTHER_USER_ID)
    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"order": 9})
    assert response.status_code == 404
    assert db_session.get(SetListEntry, entry.id).order == 1


def test_delete_another_users_entry_404_and_survives(
    client: TestClient, other_user, db_session: Session
):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    perf = _make_performance(db_session, venue.id, user_id=OTHER_USER_ID)
    entry = _make_set_list_entry_row(db_session, perf.id, work.id, user_id=OTHER_USER_ID)
    assert client.delete(f"/v1/set-list-entries/{entry.id}").status_code == 404
    assert db_session.get(SetListEntry, entry.id) is not None


def test_set_list_entries_require_auth(unauth_client: TestClient):
    assert unauth_client.post("/v1/set-list-entries/", json=_entry_payload("p", "w")).status_code == 401
    assert unauth_client.put("/v1/set-list-entries/x", json={"order": 2}).status_code == 401
    assert unauth_client.delete("/v1/set-list-entries/x").status_code == 401
