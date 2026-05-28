import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.composer import Composer


def test_get_composers_empty(client: TestClient):
    response = client.get("/v1/composers/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_composers_returns_all(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Bach", sort_name="Bach, Johann Sebastian", open_opus_id="1"))
    db_session.add(Composer(name="Mozart", sort_name="Mozart, Wolfgang Amadeus"))
    db_session.commit()

    response = client.get("/v1/composers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {c["name"] for c in data} == {"Bach", "Mozart"}


def test_get_composer_by_id(client: TestClient, db_session: Session):
    composer = Composer(name="Beethoven", sort_name="Beethoven, Ludwig van", open_opus_id="2")
    db_session.add(composer)
    db_session.commit()
    db_session.refresh(composer)

    response = client.get(f"/v1/composers/{composer.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Beethoven"
    assert data["sortName"] == "Beethoven, Ludwig van"
    assert data["openOpusId"] == "2"
    assert data["id"] == composer.id


def test_get_composer_not_found(client: TestClient):
    response = client.get("/v1/composers/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Composer not found"


def test_create_composer(client: TestClient):
    payload = {"name": "Brahms", "sortName": "Brahms, Johannes", "openOpusId": "3"}
    response = client.post("/v1/composers/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Brahms"
    assert data["sortName"] == "Brahms, Johannes"
    assert data["openOpusId"] == "3"
    assert "id" in data


def test_create_composer_minimal(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Schubert"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Schubert"
    assert data["sortName"] is None
    assert data["openOpusId"] is None


def test_create_composer_deduplication(client: TestClient, db_session: Session):
    existing = Composer(name="Handel", open_opus_id="4")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post("/v1/composers/", json={"name": "Handel", "openOpusId": "4"})
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_create_composer_no_open_opus_creates_new(client: TestClient):
    client.post("/v1/composers/", json={"name": "Anonymous"})
    client.post("/v1/composers/", json={"name": "Anonymous"})

    response = client.get("/v1/composers/")
    assert len(response.json()) == 2


def test_get_composers_filter_by_name(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Bach", sort_name="Bach, Johann Sebastian"))
    db_session.add(Composer(name="Mozart", sort_name="Mozart, Wolfgang Amadeus"))
    db_session.commit()

    response = client.get("/v1/composers/?name=Bach")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Bach"


def test_get_composers_filter_by_name_no_match(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Bach"))
    db_session.commit()

    response = client.get("/v1/composers/?name=Beethoven")
    assert response.status_code == 200
    assert response.json() == []


def test_get_composers_filter_by_name_case_insensitive(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Bach"))
    db_session.commit()

    response = client.get("/v1/composers/?name=bach")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_composers_filter_by_name_partial_match(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Johann Sebastian Bach"))
    db_session.add(Composer(name="Carl Philipp Emanuel Bach"))
    db_session.add(Composer(name="Mozart"))
    db_session.commit()

    response = client.get("/v1/composers/?name=Bach")
    assert response.status_code == 200
    assert len(response.json()) == 2
