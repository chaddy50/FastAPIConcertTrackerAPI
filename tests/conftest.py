import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Base
from app.models.composer import Composer
from app.models.enums import PerformerType, PerformanceStatus
from app.models.performance import Performance
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry
from app.models.user import User
from app.models.venue import Venue
from app.models.work import Work
from app.auth import hash_api_key

# Fixed primary/other identities so helpers can stamp ownership without a fixture
# handle, and the authed clients can present a known key.
PRIMARY_USER_ID = "10000000-0000-0000-0000-000000000001"
PRIMARY_API_KEY = "primary-user-test-key"
OTHER_USER_ID = "20000000-0000-0000-0000-000000000002"
OTHER_API_KEY = "other-user-test-key"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    # Session joins the existing transaction; route-handler commits become
    # savepoint releases so the outer rollback can undo all test data.
    session = Session(connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _make_user(db_session: Session, user_id: str, username: str, api_key: str) -> User:
    user = User(id=user_id, username=username, api_key_hash=hash_api_key(api_key))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def user(db_session: Session) -> User:
    """Primary authenticated identity for the suite."""
    return _make_user(db_session, PRIMARY_USER_ID, "primary", PRIMARY_API_KEY)


@pytest.fixture()
def other_user(db_session: Session) -> User:
    """Second identity for cross-user isolation tests."""
    return _make_user(db_session, OTHER_USER_ID, "secondary", OTHER_API_KEY)


@pytest.fixture()
def client(db_session: Session, user: User):
    """Default client, authenticated as the primary `user`."""
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {PRIMARY_API_KEY}"
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def unauth_client(db_session: Session):
    """Client with no Authorization header, for 401 paths."""
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def other_client(db_session: Session, other_user: User):
    """Client authenticated as `other_user`, for cross-user isolation tests."""
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {OTHER_API_KEY}"
        yield test_client
    app.dependency_overrides.clear()


def _make_venue(db_session: Session) -> Venue:
    venue = Venue(name="Carnegie Hall", osm_type="relation", osm_id=123456)
    db_session.add(venue)
    db_session.commit()
    db_session.refresh(venue)
    return venue


def _make_performer(
    db_session: Session,
    name: str = "Berlin Philharmonic",
    type: PerformerType = PerformerType.ORCHESTRA,
) -> Performer:
    performer = Performer(name=name, type=type)
    db_session.add(performer)
    db_session.commit()
    db_session.refresh(performer)
    return performer


def _make_work(db_session: Session) -> Work:
    composer = Composer(name="Bach")
    db_session.add(composer)
    db_session.flush()
    work = Work(title="Brandenburg Concerto No. 1")
    work.composers = [composer]
    db_session.add(work)
    db_session.commit()
    db_session.refresh(work)
    return work


def _make_performance(
    db_session: Session, venue_id: str, user_id: str = PRIMARY_USER_ID
) -> Performance:
    p = Performance(
        date=datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc),
        status=PerformanceStatus.ATTENDED,
        venue_id=venue_id,
        user_id=user_id,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _make_set_list_entry_row(
    db_session: Session,
    performance_id: str,
    work_id: str,
    order: int = 1,
    user_id: str = PRIMARY_USER_ID,
) -> SetListEntry:
    entry = SetListEntry(
        performance_id=performance_id, work_id=work_id, order=order, user_id=user_id
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry
