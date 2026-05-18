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
from app.models.venue import Venue
from app.models.work import Work


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


@pytest.fixture()
def client(db_session: Session):
    app.dependency_overrides[get_session] = lambda: (yield db_session)
    with TestClient(app) as test_client:
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


def _make_performance(db_session: Session, venue_id: str) -> Performance:
    p = Performance(
        date=datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc),
        status=PerformanceStatus.ATTENDED,
        venue_id=venue_id,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p
