from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.venue import Venue


def test_get_venues_empty(client: TestClient):
    response = client.get("/v1/venues/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_venues_returns_all(client: TestClient, db_session: Session):
    db_session.add(Venue(name="Carnegie Hall", osm_type="way", osm_id=1))
    db_session.add(Venue(name="Royal Albert Hall", osm_type="way", osm_id=2))
    db_session.commit()

    response = client.get("/v1/venues/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_venue_by_id(client: TestClient, db_session: Session):
    venue = Venue(name="Carnegie Hall", city="New York", country="US", osm_type="way", osm_id=12345)
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)

    response = client.get(f"/v1/venues/{venue.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Carnegie Hall"
    assert data["city"] == "New York"
    assert data["country"] == "US"
    assert data["osm_type"] == "way"
    assert data["osm_id"] == "12345"  # VenueRead coerces BigInt to string
    assert data["id"] == venue.id


def test_get_venue_not_found(client: TestClient):
    response = client.get("/v1/venues/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"


def test_create_venue(client: TestClient):
    payload = {"name": "Carnegie Hall", "city": "New York", "osm_type": "way", "osm_id": 12345}
    response = client.post("/v1/venues/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Carnegie Hall"
    assert data["osm_type"] == "way"
    assert data["osm_id"] == "12345"
    assert "id" in data


def test_create_venue_deduplication(client: TestClient, db_session: Session):
    existing = Venue(name="Carnegie Hall", osm_type="way", osm_id=12345)
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    response = client.post("/v1/venues/", json={"osm_type": "way", "osm_id": 12345})
    assert response.status_code == 201
    assert response.json()["id"] == existing.id


def test_update_venue(client: TestClient, db_session: Session):
    venue = Venue(name="Old Name", city="Old City", osm_type="way", osm_id=1)
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)

    response = client.patch(f"/v1/venues/{venue.id}", json={"name": "New Name", "city": "New City"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["city"] == "New City"
    assert data["osm_type"] == "way"  # unchanged


def test_update_venue_not_found(client: TestClient):
    response = client.patch("/v1/venues/nonexistent-id", json={"name": "New Name"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"


def test_delete_venue(client: TestClient, db_session: Session):
    venue = Venue(name="Carnegie Hall", osm_type="way", osm_id=1)
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)

    response = client.delete(f"/v1/venues/{venue.id}")
    assert response.status_code == 204
    assert client.get(f"/v1/venues/{venue.id}").status_code == 404


def test_delete_venue_not_found(client: TestClient):
    response = client.delete("/v1/venues/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Venue not found"
