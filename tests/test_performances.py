from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformanceStatus
from app.models.performance import Performance
from tests.conftest import _make_performance, _make_performer, _make_venue, _make_work


def test_get_performances_empty(client: TestClient):
    response = client.get("/v1/performances/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_performances_returns_all(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _make_performance(db_session, venue.id)
    p2 = Performance(
        date=datetime(2024, 3, 20, 20, 0, tzinfo=timezone.utc),
        status=PerformanceStatus.ATTENDED,
        venue_id=venue.id,
    )
    db_session.add(p2)
    db_session.commit()

    response = client.get("/v1/performances/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["date"].startswith("2024-03-20")


def test_get_performance_by_id(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.get(f"/v1/performances/{performance.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == performance.id
    assert data["status"] == "ATTENDED"
    assert data["venue"]["name"] == "Carnegie Hall"
    assert data["performers"] == []
    assert data["setList"] == []


def test_get_performance_not_found(client: TestClient):
    response = client.get("/v1/performances/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_create_performance_minimal(client: TestClient):
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venue": {"osmType": "relation", "osmId": 111111, "name": "Carnegie Hall"},
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ATTENDED"
    assert data["venue"]["name"] == "Carnegie Hall"
    assert data["performers"] == []
    assert data["setList"] == []
    assert "id" in data


def test_create_performance_with_performers(client: TestClient):
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "UPCOMING",
        "venue": {"osmType": "relation", "osmId": 222222},
        "performers": [
            {"name": "Gustavo Dudamel", "type": "CONDUCTOR"},
            {"name": "Berlin Philharmonic", "type": "ORCHESTRA"},
        ],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["performers"]) == 2
    names = {p["name"] for p in data["performers"]}
    assert "Gustavo Dudamel" in names
    assert "Berlin Philharmonic" in names


def test_create_performance_with_set_list(client: TestClient):
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venue": {"osmType": "relation", "osmId": 333333},
        "setList": [
            {
                "order": 1,
                "work": {"title": "Brandenburg Concerto No. 1", "composers": [{"name": "Bach"}]},
            },
            {
                "order": 2,
                "work": {"title": "Symphony No. 9", "composers": [{"name": "Beethoven"}]},
            },
        ],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["setList"]) == 2
    orders = {e["order"] for e in data["setList"]}
    assert orders == {1, 2}


def test_update_performance_status(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.put(f"/v1/performances/{performance.id}", json={"status": "CANCELLED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_update_performance_performers(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performer = _make_performer(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.put(
        f"/v1/performances/{performance.id}", json={"performerIds": [performer.id]}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["performers"]) == 1
    assert data["performers"][0]["id"] == performer.id



def test_update_performance_not_found(client: TestClient):
    response = client.put("/v1/performances/nonexistent-id", json={"status": "CANCELLED"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_update_performance_venue_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.put(
        f"/v1/performances/{performance.id}", json={"venueId": "nonexistent-id"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"



def test_update_performance_performer_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.put(
        f"/v1/performances/{performance.id}", json={"performerIds": ["nonexistent-id"]}
    )
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


def test_delete_performance(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.delete(f"/v1/performances/{performance.id}")
    assert response.status_code == 204
    assert client.get(f"/v1/performances/{performance.id}").status_code == 404


def test_delete_performance_not_found(client: TestClient):
    response = client.delete("/v1/performances/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"
