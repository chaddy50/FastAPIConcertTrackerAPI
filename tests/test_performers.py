from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformerType
from app.models.performer import Performer

PERFORMER_ID = "77777777-7777-7777-7777-777777777777"


def test_get_performers_empty(client: TestClient):
    response = client.get("/v1/performers/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_performers_returns_all(client: TestClient, db_session: Session):
    db_session.add(Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.add(Performer(name="Gustavo Dudamel", type=PerformerType.CONDUCTOR))
    db_session.commit()

    response = client.get("/v1/performers/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_performer_by_id(client: TestClient, db_session: Session):
    performer = Performer(
        name="Berlin Philharmonic",
        sort_name="Berlin Philharmonic",
        type=PerformerType.ORCHESTRA,
        musicbrainz_id="abc-123",
    )
    db_session.add(performer)
    db_session.commit()
    db_session.refresh(performer)

    response = client.get(f"/v1/performers/{performer.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Berlin Philharmonic"
    assert data["sort_name"] == "Berlin Philharmonic"
    assert data["type"] == "ORCHESTRA"
    assert data["musicbrainz_id"] == "abc-123"
    assert data["id"] == performer.id


def test_get_performer_not_found(client: TestClient):
    response = client.get("/v1/performers/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Performer not found"


def test_create_performer(client: TestClient):
    payload = {
        "name": "Berlin Philharmonic",
        "sort_name": "Berlin Philharmonic",
        "type": "ORCHESTRA",
        "musicbrainz_id": "abc-123",
    }
    response = client.post("/v1/performers/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Berlin Philharmonic"
    assert data["type"] == "ORCHESTRA"
    assert data["musicbrainz_id"] == "abc-123"
    assert "id" in data


def test_create_performer_deduplication(client: TestClient, db_session: Session):
    existing = Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA, musicbrainz_id="abc-123")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/performers/",
        json={"name": "Berlin Philharmonic", "type": "ORCHESTRA", "musicbrainz_id": "abc-123"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_create_performer_no_musicbrainz_id_creates_new(client: TestClient):
    client.post("/v1/performers/", json={"name": "Anonymous", "type": "SOLO"})
    client.post("/v1/performers/", json={"name": "Anonymous", "type": "SOLO"})

    response = client.get("/v1/performers/")
    assert len(response.json()) == 2


def test_get_performers_filter_by_name(client: TestClient, db_session: Session):
    db_session.add(Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.add(Performer(name="Gustavo Dudamel", type=PerformerType.CONDUCTOR))
    db_session.commit()

    response = client.get("/v1/performers/?name=Berlin")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Berlin Philharmonic"


def test_get_performers_filter_by_name_no_match(client: TestClient, db_session: Session):
    db_session.add(Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.commit()

    response = client.get("/v1/performers/?name=Vienna")
    assert response.status_code == 200
    assert response.json() == []


def test_get_performers_filter_by_name_case_insensitive(client: TestClient, db_session: Session):
    db_session.add(Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.commit()

    response = client.get("/v1/performers/?name=berlin")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_performers_filter_by_name_partial_match(client: TestClient, db_session: Session):
    db_session.add(Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.add(Performer(name="Vienna Philharmonic", type=PerformerType.ORCHESTRA))
    db_session.add(Performer(name="Gustavo Dudamel", type=PerformerType.CONDUCTOR))
    db_session.commit()

    response = client.get("/v1/performers/?name=Philharmonic")
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Client-supplied id (custom performers) -------------------------------


def _performer_payload(**extra) -> dict:
    return {"name": "Custom Ensemble", "type": "ORCHESTRA", **extra}


def test_create_performer_with_client_id_echoed(client: TestClient):
    response = client.post("/v1/performers/", json=_performer_payload(id=PERFORMER_ID))
    assert response.status_code == 201
    assert response.json()["id"] == PERFORMER_ID


def test_create_performer_id_omitted_autogenerates(client: TestClient):
    response = client.post("/v1/performers/", json=_performer_payload())
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_performer_id_null_autogenerates(client: TestClient):
    response = client.post("/v1/performers/", json=_performer_payload(id=None))
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_performer_malformed_id_422(client: TestClient):
    response = client.post("/v1/performers/", json=_performer_payload(id="nope"))
    assert response.status_code == 422


def test_create_performer_colliding_id_409(client: TestClient):
    client.post("/v1/performers/", json=_performer_payload(id=PERFORMER_ID))
    response = client.post("/v1/performers/", json=_performer_payload(id=PERFORMER_ID))
    assert response.status_code == 409


def test_create_performer_natural_key_dedup_ignores_client_id(
    client: TestClient, db_session: Session
):
    existing = Performer(name="Berlin Phil", type=PerformerType.ORCHESTRA, musicbrainz_id="mb-1")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/performers/", json=_performer_payload(musicbrainz_id="mb-1", id=PERFORMER_ID)
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id
