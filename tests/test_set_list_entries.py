from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformerType
from app.models.set_list_entry import SetListEntry
from tests.conftest import (
    PRIMARY_USER_ID,
    _make_performance,
    _make_performer,
    _make_venue,
    _make_work,
)


def _make_set_list_entry(
    db_session: Session, performance_id: str, work_id: str, order: int = 1
) -> SetListEntry:
    entry = SetListEntry(
        performance_id=performance_id, work_id=work_id, order=order, user_id=PRIMARY_USER_ID
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_create_set_list_entry(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)

    payload = {
        "performance_id": performance.id,
        "work_id": work.id,
        "order": 1,
        "featured_performers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["order"] == 1
    assert data["work"]["id"] == work.id
    assert data["notes"] is None
    assert data["featured_performers"] == []


def test_create_set_list_entry_with_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)

    payload = {
        "performance_id": performance.id,
        "work_id": work.id,
        "order": 1,
        "notes": "World premiere",
        "featured_performers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 201
    assert response.json()["notes"] == "World premiere"


def test_create_set_list_entry_with_featured_performers(
    client: TestClient, db_session: Session
):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    soloist = _make_performer(db_session, name="Yo-Yo Ma", type=PerformerType.SOLO)

    payload = {
        "performance_id": performance.id,
        "work_id": work.id,
        "order": 1,
        "featured_performers": [{"performer_id": soloist.id, "role": "Cello"}],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["featured_performers"]) == 1
    assert data["featured_performers"][0]["performer"]["name"] == "Yo-Yo Ma"
    assert data["featured_performers"][0]["role"] == "Cello"


def test_create_set_list_entry_performance_not_found(client: TestClient, db_session: Session):
    work = _make_work(db_session)

    payload = {
        "performance_id": "nonexistent-id",
        "work_id": work.id,
        "order": 1,
        "featured_performers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_create_set_list_entry_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    payload = {
        "performance_id": performance.id,
        "work_id": "nonexistent-id",
        "order": 1,
        "featured_performers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Work not found"



def test_create_set_list_entry_featured_performer_not_found(
    client: TestClient, db_session: Session
):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)

    payload = {
        "performance_id": performance.id,
        "work_id": work.id,
        "order": 1,
        "featured_performers": [{"performer_id": "nonexistent-id", "role": "Violin"}],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


def test_update_set_list_entry_order_and_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work.id, order=1)

    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"order": 2, "notes": "Encore"})
    assert response.status_code == 200
    data = response.json()
    assert data["order"] == 2
    assert data["notes"] == "Encore"


def test_update_set_list_entry_work(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work1 = _make_work(db_session)
    work2 = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work1.id, order=1)

    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"work_id": work2.id})
    assert response.status_code == 200
    assert response.json()["work"]["id"] == work2.id


def test_update_set_list_entry_replace_featured_performers(
    client: TestClient, db_session: Session
):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    soloist1 = _make_performer(db_session, name="Yo-Yo Ma", type=PerformerType.SOLO)
    soloist2 = _make_performer(db_session, name="Lang Lang", type=PerformerType.SOLO)
    entry = _make_set_list_entry(db_session, performance.id, work.id, order=1)

    client.put(
        f"/v1/set-list-entries/{entry.id}",
        json={"featured_performers": [{"performer_id": soloist1.id, "role": "Cello"}]},
    )
    response = client.put(
        f"/v1/set-list-entries/{entry.id}",
        json={"featured_performers": [{"performer_id": soloist2.id, "role": "Piano"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["featured_performers"]) == 1
    assert data["featured_performers"][0]["performer"]["name"] == "Lang Lang"
    assert data["featured_performers"][0]["role"] == "Piano"


def test_update_set_list_entry_not_found(client: TestClient):
    response = client.put("/v1/set-list-entries/nonexistent-id", json={"order": 2})
    assert response.status_code == 404
    assert response.json()["detail"] == "Set list entry not found"


def test_update_set_list_entry_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work.id)

    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"work_id": "nonexistent-id"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Work not found"



def test_update_set_list_entry_featured_performer_not_found(
    client: TestClient, db_session: Session
):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work.id)

    response = client.put(
        f"/v1/set-list-entries/{entry.id}",
        json={"featured_performers": [{"performer_id": "nonexistent-id", "role": "Violin"}]},
    )
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


def test_delete_set_list_entry(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work.id)

    response = client.delete(f"/v1/set-list-entries/{entry.id}")
    assert response.status_code == 204
    assert client.delete(f"/v1/set-list-entries/{entry.id}").status_code == 404


def test_delete_set_list_entry_not_found(client: TestClient):
    response = client.delete("/v1/set-list-entries/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Set list entry not found"


# --- Client-supplied id ---------------------------------------------------

ENTRY_ID = "55555555-5555-5555-5555-555555555555"


def _entry_payload(performance_id: str, work_id: str, **extra) -> dict:
    return {
        "performance_id": performance_id,
        "work_id": work_id,
        "order": 1,
        "featured_performers": [],
        **extra,
    }


def test_create_set_list_entry_with_client_id_echoed(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    response = client.post(
        "/v1/set-list-entries/", json=_entry_payload(performance.id, work.id, id=ENTRY_ID)
    )
    assert response.status_code == 201
    assert response.json()["id"] == ENTRY_ID


def test_create_set_list_entry_id_omitted_autogenerates(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    response = client.post("/v1/set-list-entries/", json=_entry_payload(performance.id, work.id))
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_set_list_entry_id_null_autogenerates(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    response = client.post(
        "/v1/set-list-entries/", json=_entry_payload(performance.id, work.id, id=None)
    )
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_set_list_entry_malformed_id_422(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    response = client.post(
        "/v1/set-list-entries/", json=_entry_payload(performance.id, work.id, id="nope")
    )
    assert response.status_code == 422


def test_create_set_list_entry_colliding_id_409(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    client.post("/v1/set-list-entries/", json=_entry_payload(performance.id, work.id, id=ENTRY_ID))
    response = client.post(
        "/v1/set-list-entries/",
        json=_entry_payload(performance.id, work.id, id=ENTRY_ID, order=9),
    )
    assert response.status_code == 409


def test_create_set_list_entry_persisted_under_client_id(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    client.post("/v1/set-list-entries/", json=_entry_payload(performance.id, work.id, id=ENTRY_ID))
    response = client.delete(f"/v1/set-list-entries/{ENTRY_ID}")
    assert response.status_code == 204
