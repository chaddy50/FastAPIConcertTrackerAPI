from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformanceStatus
from app.models.performance import Performance
from app.models.set_list_entry import SetListEntry
from tests.conftest import _make_performance, _make_performer, _make_venue, _make_work

PERF_ID = "11111111-1111-1111-1111-111111111111"
PERF_ID_2 = "22222222-2222-2222-2222-222222222222"
ENTRY_ID = "33333333-3333-3333-3333-333333333333"
ENTRY_ID_2 = "44444444-4444-4444-4444-444444444444"


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
    assert data["set_list"] == []


def test_get_performance_not_found(client: TestClient):
    response = client.get("/v1/performances/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Performance not found"


def test_create_performance_minimal(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venue_id": venue.id,
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ATTENDED"
    assert data["venue"]["name"] == "Carnegie Hall"
    assert data["performers"] == []
    assert data["set_list"] == []
    assert "id" in data


def test_create_performance_venue_not_found(client: TestClient):
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "venue_id": "nonexistent-id",
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
        "venue_id": venue.id,
        "performer_ids": [p1.id, p2.id],
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
        "venue_id": venue.id,
        "performer_ids": ["nonexistent-id"],
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
        "venue_id": venue.id,
        "set_list": [
            {"order": 1, "work_id": work1.id},
        ],
    }
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["set_list"]) == 1
    assert data["set_list"][0]["order"] == 1


def test_create_performance_work_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    payload = {
        "date": "2024-01-15T20:00:00+00:00",
        "venue_id": venue.id,
        "set_list": [{"order": 1, "work_id": "nonexistent-id"}],
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
        f"/v1/performances/{performance.id}", json={"performer_ids": [performer.id]}
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
        f"/v1/performances/{performance.id}", json={"venue_id": "nonexistent-id"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"



def test_update_performance_performer_not_found(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)

    response = client.put(
        f"/v1/performances/{performance.id}", json={"performer_ids": ["nonexistent-id"]}
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


# --- Performance-level notes ----------------------------------------------


def _notes_payload(venue_id: str, **extra) -> dict:
    return {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venue_id": venue_id,
        **extra,
    }


def test_create_performance_with_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post(
        "/v1/performances/", json=_notes_payload(venue.id, notes="Great night out")
    )
    assert response.status_code == 201
    assert response.json()["notes"] == "Great night out"


def test_create_performance_notes_omitted_is_null(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_notes_payload(venue.id))
    assert response.status_code == 201
    assert response.json()["notes"] is None


def test_create_performance_notes_explicit_null(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_notes_payload(venue.id, notes=None))
    assert response.status_code == 201
    assert response.json()["notes"] is None


def test_create_performance_notes_empty_string_preserved(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_notes_payload(venue.id, notes=""))
    assert response.status_code == 201
    assert response.json()["notes"] == ""


def test_create_performance_notes_non_string_422(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_notes_payload(venue.id, notes=123))
    assert response.status_code == 422


def test_create_performance_notes_persisted(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    created = client.post(
        "/v1/performances/", json=_notes_payload(venue.id, notes="Durable note")
    )
    performance_id = created.json()["id"]
    response = client.get(f"/v1/performances/{performance_id}")
    assert response.status_code == 200
    assert response.json()["notes"] == "Durable note"


def test_create_performance_notes_independent_from_entry_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    payload = _notes_payload(
        venue.id,
        notes="Concert-level note",
        set_list=[{"order": 1, "work_id": work.id, "notes": "Entry-level note"}],
    )
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] == "Concert-level note"
    assert data["set_list"][0]["notes"] == "Entry-level note"


def test_get_performance_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    created = client.post("/v1/performances/", json=_notes_payload(venue.id, notes="Seen it"))
    performance_id = created.json()["id"]
    response = client.get(f"/v1/performances/{performance_id}")
    assert response.status_code == 200
    assert response.json()["notes"] == "Seen it"


def test_get_performance_notes_null_when_absent(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    response = client.get(f"/v1/performances/{performance.id}")
    assert response.status_code == 200
    assert response.json()["notes"] is None


def test_get_performances_list_includes_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    client.post("/v1/performances/", json=_notes_payload(venue.id, notes="Has notes"))
    client.post("/v1/performances/", json=_notes_payload(venue.id))
    response = client.get("/v1/performances/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    notes = {item["notes"] for item in data}
    assert notes == {"Has notes", None}


def test_update_performance_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    response = client.put(
        f"/v1/performances/{performance.id}", json={"notes": "Newly added"}
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Newly added"


def test_update_performance_notes_overwrites(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    created = client.post("/v1/performances/", json=_notes_payload(venue.id, notes="Old"))
    performance_id = created.json()["id"]
    response = client.put(f"/v1/performances/{performance_id}", json={"notes": "New"})
    assert response.status_code == 200
    assert response.json()["notes"] == "New"


def test_update_performance_notes_clear_to_null(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    created = client.post("/v1/performances/", json=_notes_payload(venue.id, notes="To clear"))
    performance_id = created.json()["id"]
    response = client.put(f"/v1/performances/{performance_id}", json={"notes": None})
    assert response.status_code == 200
    assert response.json()["notes"] is None


def test_update_performance_omitting_notes_preserves_them(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    created = client.post("/v1/performances/", json=_notes_payload(venue.id, notes="Keep me"))
    performance_id = created.json()["id"]
    response = client.put(f"/v1/performances/{performance_id}", json={"status": "CANCELLED"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert data["notes"] == "Keep me"


def test_update_performance_omitting_notes_leaves_null_null(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    response = client.put(f"/v1/performances/{performance.id}", json={"status": "CANCELLED"})
    assert response.status_code == 200
    assert response.json()["notes"] is None


def test_update_performance_notes_persisted(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    client.put(f"/v1/performances/{performance.id}", json={"notes": "Updated note"})
    response = client.get(f"/v1/performances/{performance.id}")
    assert response.status_code == 200
    assert response.json()["notes"] == "Updated note"


def test_update_performance_notes_non_string_422(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    performance = _make_performance(db_session, venue.id)
    response = client.put(f"/v1/performances/{performance.id}", json={"notes": 123})
    assert response.status_code == 422


def test_update_performance_notes_leaves_entry_notes(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    created = client.post(
        "/v1/performances/",
        json=_notes_payload(
            venue.id,
            set_list=[{"order": 1, "work_id": work.id, "notes": "Entry note"}],
        ),
    )
    performance_id = created.json()["id"]
    response = client.put(f"/v1/performances/{performance_id}", json={"notes": "Perf note"})
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == "Perf note"
    assert data["set_list"][0]["notes"] == "Entry note"


# --- Client-supplied id ---------------------------------------------------


def _perf_payload(venue_id: str, **extra) -> dict:
    return {
        "date": "2024-01-15T20:00:00+00:00",
        "status": "ATTENDED",
        "venue_id": venue_id,
        **extra,
    }


def test_create_performance_with_client_id_echoed(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID))
    assert response.status_code == 201
    assert response.json()["id"] == PERF_ID


def test_create_performance_with_client_id_persisted(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID))
    response = client.get(f"/v1/performances/{PERF_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == PERF_ID


def test_create_performance_id_omitted_autogenerates(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_perf_payload(venue.id))
    assert response.status_code == 201
    UUID(response.json()["id"])  # parseable, non-null


def test_create_performance_id_null_autogenerates(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_perf_payload(venue.id, id=None))
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_performance_malformed_id_422(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_perf_payload(venue.id, id="not-a-uuid"))
    assert response.status_code == 422


def test_create_performance_empty_string_id_422(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    response = client.post("/v1/performances/", json=_perf_payload(venue.id, id=""))
    assert response.status_code == 422


def test_create_performance_colliding_id_409(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID))
    response = client.post(
        "/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID, status="UPCOMING")
    )
    assert response.status_code == 409


def test_create_performance_collision_is_noop(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID))
    client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID, status="UPCOMING"))
    response = client.get(f"/v1/performances/{PERF_ID}")
    assert response.json()["status"] == "ATTENDED"  # original, not overwritten


def test_create_performance_bad_venue_precedes_collision(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    client.post("/v1/performances/", json=_perf_payload(venue.id, id=PERF_ID))
    response = client.post("/v1/performances/", json=_perf_payload("nonexistent-venue", id=PERF_ID))
    assert response.status_code == 404


def test_create_performance_inline_entry_client_id_echoed(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    payload = _perf_payload(
        venue.id,
        id=PERF_ID,
        set_list=[{"id": ENTRY_ID, "order": 1, "work_id": work.id}],
    )
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    assert response.json()["set_list"][0]["id"] == ENTRY_ID


def test_create_performance_inline_entry_collision_rolls_back(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    existing = SetListEntry(id=ENTRY_ID, performance_id=_make_performance(db_session, venue.id).id, work_id=work.id, order=1)
    db_session.add(existing)
    db_session.commit()

    payload = _perf_payload(
        venue.id,
        id=PERF_ID,
        set_list=[{"id": ENTRY_ID, "order": 1, "work_id": work.id}],
    )
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 409
    # Whole request rolled back: the parent performance was not persisted.
    assert client.get(f"/v1/performances/{PERF_ID}").status_code == 404


def test_create_performance_duplicate_inline_entry_ids_409(client: TestClient, db_session: Session):
    venue = _make_venue(db_session)
    work = _make_work(db_session)
    payload = _perf_payload(
        venue.id,
        set_list=[
            {"id": ENTRY_ID, "order": 1, "work_id": work.id},
            {"id": ENTRY_ID, "order": 2, "work_id": work.id},
        ],
    )
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 409


def test_offline_graph_custom_entities_resolve_by_client_id(client: TestClient, db_session: Session):
    """End-to-end: custom performer + work created under client ids, then a performance
    referencing them by those same ids — no remapping, no 404."""
    venue = _make_venue(db_session)
    performer_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    work_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    assert client.post(
        "/v1/performers/", json={"name": "Custom Ensemble", "type": "ORCHESTRA", "id": performer_id}
    ).status_code == 201
    assert client.post(
        "/v1/works/", json={"title": "Custom Work", "id": work_id, "composers": [{"name": "X"}]}
    ).status_code == 201

    payload = _perf_payload(
        venue.id,
        id=PERF_ID,
        performer_ids=[performer_id],
        set_list=[
            {
                "id": ENTRY_ID,
                "order": 1,
                "work_id": work_id,
                "featured_performers": [{"performer_id": performer_id, "role": "Cello"}],
            }
        ],
    )
    response = client.post("/v1/performances/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == PERF_ID
    assert data["performers"][0]["id"] == performer_id
    assert data["set_list"][0]["work"]["id"] == work_id
