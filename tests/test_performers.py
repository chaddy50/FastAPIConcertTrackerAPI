from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import PerformerType
from app.models.performer import Performer


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
    assert data["sortName"] == "Berlin Philharmonic"
    assert data["type"] == "ORCHESTRA"
    assert data["musicbrainzId"] == "abc-123"
    assert data["id"] == performer.id


def test_get_performer_not_found(client: TestClient):
    response = client.get("/v1/performers/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Performer not found"


def test_create_performer(client: TestClient):
    payload = {
        "name": "Berlin Philharmonic",
        "sortName": "Berlin Philharmonic",
        "type": "ORCHESTRA",
        "musicbrainzId": "abc-123",
    }
    response = client.post("/v1/performers/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Berlin Philharmonic"
    assert data["type"] == "ORCHESTRA"
    assert data["musicbrainzId"] == "abc-123"
    assert "id" in data


def test_create_performer_deduplication(client: TestClient, db_session: Session):
    existing = Performer(name="Berlin Philharmonic", type=PerformerType.ORCHESTRA, musicbrainz_id="abc-123")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/performers/",
        json={"name": "Berlin Philharmonic", "type": "ORCHESTRA", "musicbrainzId": "abc-123"},
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_create_performer_no_musicbrainz_id_creates_new(client: TestClient):
    client.post("/v1/performers/", json={"name": "Anonymous", "type": "SOLO"})
    client.post("/v1/performers/", json={"name": "Anonymous", "type": "SOLO"})

    response = client.get("/v1/performers/")
    assert len(response.json()) == 2
