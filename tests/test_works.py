from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.composer import Composer
from app.models.work import Work

WORK_ID = "88888888-8888-8888-8888-888888888888"
COMPOSER_ID = "99999999-9999-9999-9999-999999999999"


def _make_composer(db_session: Session, name: str = "Bach") -> Composer:
    composer = Composer(name=name)
    db_session.add(composer)
    db_session.commit()
    db_session.refresh(composer)
    return composer


def test_get_works_empty(client: TestClient):
    response = client.get("/v1/works/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_works_returns_all(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work1 = Work(title="Brandenburg Concerto No. 1")
    work1.composers = [composer]
    work2 = Work(title="Brandenburg Concerto No. 2")
    work2.composers = [composer]
    db_session.add_all([work1, work2])
    db_session.commit()

    response = client.get("/v1/works/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_work_by_id(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work = Work(title="Brandenburg Concerto No. 1", key="F major", catalog_number="BWV 1046", open_opus_id="5")
    work.composers = [composer]
    db_session.add(work)
    db_session.commit()
    db_session.refresh(work)

    response = client.get(f"/v1/works/{work.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Brandenburg Concerto No. 1"
    assert data["key"] == "F major"
    assert data["catalog_number"] == "BWV 1046"
    assert data["open_opus_id"] == "5"
    assert len(data["composers"]) == 1
    assert data["composers"][0]["name"] == "Bach"
    assert data["id"] == work.id


def test_get_work_not_found(client: TestClient):
    response = client.get("/v1/works/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Work not found"


def test_create_work(client: TestClient):
    payload = {
        "title": "Brandenburg Concerto No. 1",
        "key": "F major",
        "catalog_number": "BWV 1046",
        "composers": [{"name": "Bach"}],
    }
    response = client.post("/v1/works/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Brandenburg Concerto No. 1"
    assert data["key"] == "F major"
    assert data["catalog_number"] == "BWV 1046"
    assert len(data["composers"]) == 1
    assert data["composers"][0]["name"] == "Bach"


def test_create_work_deduplication(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    existing = Work(title="Brandenburg Concerto No. 1", open_opus_id="5")
    existing.composers = [composer]
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/works/",
        json={"title": "Brandenburg Concerto No. 1", "open_opus_id": "5", "composers": [{"name": "Bach"}]},
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_create_work_creates_composer_inline(client: TestClient):
    response = client.post(
        "/v1/works/",
        json={"title": "Well-Tempered Clavier", "composers": [{"name": "Bach", "open_opus_id": "1"}]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["composers"][0]["name"] == "Bach"
    assert data["composers"][0]["open_opus_id"] == "1"

    # Composer should now exist independently
    composers_response = client.get("/v1/composers/")
    assert any(c["open_opus_id"] == "1" for c in composers_response.json())


def test_get_works_filter_by_name(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work1 = Work(title="Brandenburg Concerto No. 1")
    work1.composers = [composer]
    work2 = Work(title="Well-Tempered Clavier")
    work2.composers = [composer]
    db_session.add_all([work1, work2])
    db_session.commit()

    response = client.get("/v1/works/?name=Brandenburg")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Brandenburg Concerto No. 1"


def test_get_works_filter_by_name_no_match(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work = Work(title="Brandenburg Concerto No. 1")
    work.composers = [composer]
    db_session.add(work)
    db_session.commit()

    response = client.get("/v1/works/?name=Symphony")
    assert response.status_code == 200
    assert response.json() == []


def test_get_works_filter_by_name_case_insensitive(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work = Work(title="Brandenburg Concerto No. 1")
    work.composers = [composer]
    db_session.add(work)
    db_session.commit()

    response = client.get("/v1/works/?name=brandenburg")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_works_filter_by_name_partial_match(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    work1 = Work(title="Brandenburg Concerto No. 1")
    work1.composers = [composer]
    work2 = Work(title="Brandenburg Concerto No. 2")
    work2.composers = [composer]
    work3 = Work(title="Well-Tempered Clavier")
    work3.composers = [composer]
    db_session.add_all([work1, work2, work3])
    db_session.commit()

    response = client.get("/v1/works/?name=Brandenburg Concerto")
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Client-supplied id (custom works + nested composers) -----------------


def test_create_work_with_client_id_echoed(client: TestClient):
    response = client.post(
        "/v1/works/", json={"title": "Custom Work", "id": WORK_ID, "composers": [{"name": "X"}]}
    )
    assert response.status_code == 201
    assert response.json()["id"] == WORK_ID


def test_create_work_with_nested_composer_client_ids(client: TestClient):
    response = client.post(
        "/v1/works/",
        json={
            "title": "Custom Work",
            "id": WORK_ID,
            "composers": [{"name": "X", "id": COMPOSER_ID}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == WORK_ID
    assert data["composers"][0]["id"] == COMPOSER_ID


def test_create_work_id_omitted_autogenerates(client: TestClient):
    response = client.post(
        "/v1/works/", json={"title": "Custom Work", "composers": [{"name": "X"}]}
    )
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_work_id_null_autogenerates(client: TestClient):
    response = client.post(
        "/v1/works/", json={"title": "Custom Work", "id": None, "composers": [{"name": "X"}]}
    )
    assert response.status_code == 201
    UUID(response.json()["id"])


def test_create_work_malformed_id_422(client: TestClient):
    response = client.post(
        "/v1/works/", json={"title": "Custom Work", "id": "nope", "composers": [{"name": "X"}]}
    )
    assert response.status_code == 422


def test_create_work_colliding_id_409(client: TestClient):
    client.post("/v1/works/", json={"title": "Custom Work", "id": WORK_ID, "composers": [{"name": "X"}]})
    response = client.post(
        "/v1/works/", json={"title": "Other", "id": WORK_ID, "composers": [{"name": "Y"}]}
    )
    assert response.status_code == 409


def test_create_work_nested_composer_collision_rolls_back(client: TestClient, db_session: Session):
    existing = Composer(name="Taken", id=COMPOSER_ID)
    db_session.add(existing)
    db_session.commit()

    response = client.post(
        "/v1/works/",
        json={"title": "Custom Work", "id": WORK_ID, "composers": [{"name": "X", "id": COMPOSER_ID}]},
    )
    assert response.status_code == 409
    # Work must not have been persisted (whole-request rollback).
    assert client.get(f"/v1/works/{WORK_ID}").status_code == 404


def test_create_work_natural_key_dedup_ignores_client_id(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    existing = Work(title="Deduped", open_opus_id="500")
    existing.composers = [composer]
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post(
        "/v1/works/",
        json={"title": "Deduped", "open_opus_id": "500", "id": WORK_ID, "composers": [{"name": "Bach"}]},
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id
