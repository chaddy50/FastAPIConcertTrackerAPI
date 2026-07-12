import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.performance import Performance
from app.models.user import User
from app.models.venue import Venue
from app.auth import hash_api_key
from tests.conftest import PRIMARY_USER_ID, _make_venue


def test_username_unique(db_session: Session, user: User):
    db_session.add(User(username="primary", api_key_hash=hash_api_key("k2")))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_api_key_hash_unique(db_session: Session, user: User):
    db_session.add(User(username="another", api_key_hash=user.api_key_hash))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_performance_user_id_not_null(db_session: Session):
    from datetime import datetime, timezone

    venue = _make_venue(db_session)
    db_session.add(
        Performance(date=datetime(2024, 1, 1, tzinfo=timezone.utc), venue_id=venue.id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_custom_venue_without_osm_inserts(db_session: Session, user: User):
    venue = Venue(name="Basement Studio", user_id=PRIMARY_USER_ID)
    db_session.add(venue)
    db_session.flush()
    assert venue.osm_type is None
    assert venue.osm_id is None
    assert venue.user_id == PRIMARY_USER_ID


def test_performance_user_id_persists(db_session: Session, user: User):
    from datetime import datetime, timezone

    venue = _make_venue(db_session)
    perf = Performance(
        date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        venue_id=venue.id,
        user_id=PRIMARY_USER_ID,
    )
    db_session.add(perf)
    db_session.flush()
    assert perf.user_id == PRIMARY_USER_ID
    assert db_session.get(User, perf.user_id).username == "primary"
