from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.models.composer import Composer, ComposerCreate
from app.models.performer import Performer, PerformerCreate
from app.models.venue import Venue, VenueCreate
from app.models.work import Work, WorkCreate


def find_or_create_composer(data: ComposerCreate, session: Session) -> Composer:
    if data.open_opus_id:
        existing = session.query(Composer).where(Composer.open_opus_id == data.open_opus_id).first()
        if existing:
            return existing
    if data.id is not None and session.get(Composer, data.id):
        raise HTTPException(status_code=409, detail=f"Composer {data.id} already exists")
    dumped = data.model_dump()
    if dumped.get("id") is None:
        dumped.pop("id", None)  # let default=lambda: str(uuid4()) apply
    composer = Composer(**dumped)
    session.add(composer)
    session.flush()
    return composer


def find_or_create_venue(data: VenueCreate, session: Session) -> Venue:
    if data.osm_type is not None and data.osm_id is not None:
        existing = session.query(Venue).where(
            Venue.osm_type == data.osm_type, Venue.osm_id == data.osm_id
        ).first()
        if existing:
            return existing
    venue = Venue(**data.model_dump())
    session.add(venue)
    session.flush()
    return venue


def find_or_create_performer(data: PerformerCreate, session: Session) -> Performer:
    if data.musicbrainz_id:
        existing = session.query(Performer).where(
            Performer.musicbrainz_id == data.musicbrainz_id
        ).first()
        if existing:
            return existing
    if data.id is not None and session.get(Performer, data.id):
        raise HTTPException(status_code=409, detail=f"Performer {data.id} already exists")
    dumped = data.model_dump()
    if dumped.get("id") is None:
        dumped.pop("id", None)  # let default=lambda: str(uuid4()) apply
    performer = Performer(**dumped)
    session.add(performer)
    session.flush()
    return performer


def find_or_create_work(data: WorkCreate, session: Session) -> Work:
    if data.open_opus_id:
        existing = session.scalars(
            session.query(Work)
            .where(Work.open_opus_id == data.open_opus_id)
            .options(selectinload(Work.composers))
        ).first()
        if existing:
            return existing
    if data.id is not None and session.get(Work, data.id):
        raise HTTPException(status_code=409, detail=f"Work {data.id} already exists")
    composers = [find_or_create_composer(c, session) for c in data.composers]
    dumped = data.model_dump(exclude={"composers"})
    if dumped.get("id") is None:
        dumped.pop("id", None)  # let default=lambda: str(uuid4()) apply
    work = Work(**dumped)
    work.composers = composers
    session.add(work)
    session.flush()
    return work
