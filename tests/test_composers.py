from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.composer import Composer

COMPOSER_ID = "66666666-6666-6666-6666-666666666666"


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
    assert data["sort_name"] == "Beethoven, Ludwig van"
    assert data["open_opus_id"] == "2"
    assert data["id"] == composer.id


def test_get_composer_not_found(client: TestClient):
    response = client.get("/v1/composers/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Composer not found"


def test_create_composer(client: TestClient):
    payload = {"name": "Brahms", "sort_name": "Brahms, Johannes", "open_opus_id": "3"}
    response = client.post("/v1/composers/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Brahms"
    assert data["sort_name"] == "Brahms, Johannes"
    assert data["open_opus_id"] == "3"
    assert "id" in data


def test_create_composer_minimal(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Schubert"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Schubert"
    assert data["sort_name"] is None
    assert data["open_opus_id"] is None


def test_create_composer_deduplication(client: TestClient, db_session: Session):
    existing = Composer(name="Handel", open_opus_id="4")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post("/v1/composers/", json={"name": "Handel", "open_opus_id": "4"})
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


# --- Epoch -----------------------------------------------------------------


def test_get_composer_by_id_returns_epoch(client: TestClient, db_session: Session):
    composer = Composer(name="Mozart", open_opus_id="196", epoch="Classical")
    db_session.add(composer)
    db_session.commit()
    db_session.refresh(composer)

    response = client.get(f"/v1/composers/{composer.id}")
    assert response.status_code == 200
    assert response.json()["epoch"] == "Classical"


def test_get_composers_list_includes_epoch(client: TestClient, db_session: Session):
    db_session.add(Composer(name="Strauss", epoch="Late Romantic"))
    db_session.commit()

    response = client.get("/v1/composers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["epoch"] == "Late Romantic"


def test_create_composer_with_epoch(client: TestClient):
    payload = {"name": "Beethoven", "open_opus_id": "145", "epoch": "Early Romantic"}
    response = client.post("/v1/composers/", json=payload)
    assert response.status_code == 201
    assert response.json()["epoch"] == "Early Romantic"


def test_create_composer_without_epoch_is_null(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Schubert"})
    assert response.status_code == 201
    assert response.json()["epoch"] is None


def test_composer_epoch_defaults_to_none(db_session: Session):
    composer = Composer(name="Bach")
    db_session.add(composer)
    db_session.commit()
    db_session.refresh(composer)
    assert composer.epoch is None


# --- Client-supplied id (custom composers) --------------------------------


def test_create_composer_with_client_id_echoed(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Custom", "id": COMPOSER_ID})
    assert response.status_code == 201
    assert response.json()["id"] == COMPOSER_ID


def test_create_composer_id_omitted_autogenerates(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Custom"})
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_composer_id_null_autogenerates(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Custom", "id": None})
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_composer_malformed_id_422(client: TestClient):
    response = client.post("/v1/composers/", json={"name": "Custom", "id": "nope"})
    assert response.status_code == 422


def test_create_composer_colliding_id_409(client: TestClient):
    client.post("/v1/composers/", json={"name": "Custom", "id": COMPOSER_ID})
    response = client.post("/v1/composers/", json={"name": "Other", "id": COMPOSER_ID})
    assert response.status_code == 409


def test_create_composer_natural_key_dedup_ignores_client_id(
    client: TestClient, db_session: Session
):
    existing = Composer(name="Handel", open_opus_id="42")
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/composers/", json={"name": "Handel", "open_opus_id": "42", "id": COMPOSER_ID}
    )
    assert response.status_code == 201
    # Dedup wins: the existing server id is returned, the supplied id is ignored.
    assert response.json()["id"] == existing.id
