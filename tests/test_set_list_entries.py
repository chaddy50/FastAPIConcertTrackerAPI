from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformerType
from app.models.set_list_entry import SetListEntry
from tests.conftest import _make_performance, _make_performer, _make_venue, _make_work


def _make_set_list_entry(
    db_session: Session, performance_id: str, work_id: str, order: int = 1
) -> SetListEntry:
    entry = SetListEntry(performance_id=performance_id, work_id=work_id, order=order)
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_create_set_list_entry(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)

    payload = {
        "performanceId": performance.id,
        "workId": work.id,
        "order": 1,
        "featuredPerformers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["order"] == 1
    assert data["work"]["id"] == work.id
    assert data["notes"] is None
    assert data["featuredPerformers"] == []


def test_create_set_list_entry_with_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)

    payload = {
        "performanceId": performance.id,
        "workId": work.id,
        "order": 1,
        "notes": "World premiere",
        "featuredPerformers": [],
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
        "performanceId": performance.id,
        "workId": work.id,
        "order": 1,
        "featuredPerformers": [{"performerId": soloist.id, "role": "Cello"}],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["featuredPerformers"]) == 1
    assert data["featuredPerformers"][0]["performer"]["name"] == "Yo-Yo Ma"
    assert data["featuredPerformers"][0]["role"] == "Cello"


def test_create_set_list_entry_performance_not_found(client: TestClient, db_session: Session):
    work = _make_work(db_session)

    payload = {
        "performanceId": "nonexistent-id",
        "workId": work.id,
        "order": 1,
        "featuredPerformers": [],
    }
    response = client.post("/v1/set-list-entries/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_create_set_list_entry_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    payload = {
        "performanceId": performance.id,
        "workId": "nonexistent-id",
        "order": 1,
        "featuredPerformers": [],
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
        "performanceId": performance.id,
        "workId": work.id,
        "order": 1,
        "featuredPerformers": [{"performerId": "nonexistent-id", "role": "Violin"}],
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

    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"workId": work2.id})
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
        json={"featuredPerformers": [{"performerId": soloist1.id, "role": "Cello"}]},
    )
    response = client.put(
        f"/v1/set-list-entries/{entry.id}",
        json={"featuredPerformers": [{"performerId": soloist2.id, "role": "Piano"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["featuredPerformers"]) == 1
    assert data["featuredPerformers"][0]["performer"]["name"] == "Lang Lang"
    assert data["featuredPerformers"][0]["role"] == "Piano"


def test_update_set_list_entry_not_found(client: TestClient):
    response = client.put("/v1/set-list-entries/nonexistent-id", json={"order": 2})
    assert response.status_code == 404
    assert response.json()["detail"] == "Set list entry not found"


def test_update_set_list_entry_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    work = _make_work(db_session)
    entry = _make_set_list_entry(db_session, performance.id, work.id)

    response = client.put(f"/v1/set-list-entries/{entry.id}", json={"workId": "nonexistent-id"})
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
        json={"featuredPerformers": [{"performerId": "nonexistent-id", "role": "Violin"}]},
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
