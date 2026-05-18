from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.composer import Composer
from app.models.work import Work


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
    assert data["catalogNumber"] == "BWV 1046"
    assert data["openOpusId"] == "5"
    assert len(data["composers"]) == 1
    assert data["composers"][0]["name"] == "Bach"
    assert data["id"] == work.id


def test_get_work_not_found(client: TestClient):
    response = client.get("/v1/works/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Work not found"


def test_create_work(client: TestClient, db_session: Session):
    composer = _make_composer(db_session)
    payload = {
        "title": "Brandenburg Concerto No. 1",
        "key": "F major",
        "catalogNumber": "BWV 1046",
        "composerIds": [composer.id],
    }
    response = client.post("/v1/works/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Brandenburg Concerto No. 1"
    assert data["key"] == "F major"
    assert data["catalogNumber"] == "BWV 1046"
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
        json={"title": "Brandenburg Concerto No. 1", "openOpusId": "5", "composerIds": [composer.id]},
    )
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_create_work_composer_not_found(client: TestClient):
    response = client.post(
        "/v1/works/",
        json={"title": "Some Work", "composerIds": ["nonexistent-composer-id"]},
    )
    assert response.status_code == 404
    assert "nonexistent-composer-id" in response.json()["detail"]
