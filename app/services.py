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
    composer = Composer(**data.model_dump())
    session.add(composer)
    session.flush()
    return composer


def find_or_create_venue(data: VenueCreate, session: Session) -> Venue:
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
    performer = Performer(**data.model_dump())
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
    composers = [find_or_create_composer(c, session) for c in data.composers]
    work = Work(**data.model_dump(exclude={"composers"}))
    work.composers = composers
    session.add(work)
    session.flush()
    return work
