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
    # Default sort is date_asc, so the earlier performance comes first.
    assert data[0]["date"].startswith("2024-01-15")


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


def test_create_performance_minimal(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venueId": venue.id,
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ATTENDED"
    assert data["venue"]["name"] == "Carnegie Hall"
    assert data["performers"] == []
    assert data["setList"] == []
    assert "id" in data


def test_create_performance_venue_not_found(client: TestClient):
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "venueId": "nonexistent-id",
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"


def test_create_performance_with_performers(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    p1 = _make_performer(db_session, name="Gustavo Dudamel")
    p2 = _make_performer(db_session, name="Berlin Philharmonic")
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "UPCOMING",
        "venueId": venue.id,
        "performerIds": [p1.id, p2.id],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["performers"]) == 2
    names = {p["name"] for p in data["performers"]}
    assert "Gustavo Dudamel" in names
    assert "Berlin Philharmonic" in names


def test_create_performance_performer_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "venueId": venue.id,
        "performerIds": ["nonexistent-id"],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


def test_create_performance_with_set_list(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work1 = _make_work(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venueId": venue.id,
        "setList": [
            {"order": 1, "workId": work1.id},
        ],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["setList"]) == 1
    assert data["setList"][0]["order"] == 1


def test_create_performance_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "venueId": venue.id,
        "setList": [{"order": 1, "workId": "nonexistent-id"}],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


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


def _add_performance(
    db_session: Session, venue_id: str, date: datetime, status: PerformanceStatus
) -> Performance:
    p = Performance(date=date, status=status, venue_id=venue_id)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def test_get_performances_filter_by_status(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)
    _add_performance(db_session, venue.id, datetime(2024, 2, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)

    response = client.get("/v1/performances/?status=UPCOMING")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "UPCOMING"


def test_get_performances_filter_by_multiple_statuses(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)
    _add_performance(db_session, venue.id, datetime(2024, 2, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 3, 1, tzinfo=timezone.utc), PerformanceStatus.CANCELLED)

    response = client.get("/v1/performances/?status=ATTENDED,CANCELLED")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {p["status"] for p in data} == {"ATTENDED", "CANCELLED"}


def test_get_performances_filter_by_status_invalid(client: TestClient, db_session: Session):
    _make_venue(db_session)
    response = client.get("/v1/performances/?status=BOGUS")
    assert response.status_code == 422
    assert "BOGUS" in response.json()["detail"]


def test_get_performances_sort_date_desc(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 6, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)

    response = client.get("/v1/performances/?sort=date_desc")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["date"].startswith("2024-06-01")
    assert data[1]["date"].startswith("2024-01-01")


def test_get_performances_sort_date_asc(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 6, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)

    response = client.get("/v1/performances/?sort=date_asc")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["date"].startswith("2024-01-01")
    assert data[1]["date"].startswith("2024-06-01")


def test_get_performances_sort_invalid(client: TestClient, db_session: Session):
    _make_venue(db_session)
    response = client.get("/v1/performances/?sort=bogus")
    assert response.status_code == 422


def test_get_performances_limit(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 2, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 3, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)

    response = client.get("/v1/performances/?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_performances_limit_must_be_positive(client: TestClient, db_session: Session):
    _make_venue(db_session)
    response = client.get("/v1/performances/?limit=0")
    assert response.status_code == 422


def test_get_performances_date_after(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 6, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)

    response = client.get(
        "/v1/performances/", params={"date_after": "2024-03-01T00:00:00+00:00"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"].startswith("2024-06-01")


def test_get_performances_combined_filters(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    _add_performance(db_session, venue.id, datetime(2024, 1, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)
    _add_performance(db_session, venue.id, datetime(2024, 6, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)
    _add_performance(db_session, venue.id, datetime(2024, 7, 1, tzinfo=timezone.utc), PerformanceStatus.ATTENDED)
    _add_performance(db_session, venue.id, datetime(2024, 8, 1, tzinfo=timezone.utc), PerformanceStatus.UPCOMING)

    response = client.get(
        "/v1/performances/",
        params={
            "status": "UPCOMING",
            "date_after": "2024-03-01T00:00:00+00:00",
            "sort": "date_desc",
            "limit": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"].startswith("2024-08-01")
    assert data[0]["status"] == "UPCOMING"
