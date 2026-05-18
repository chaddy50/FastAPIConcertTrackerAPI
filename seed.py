"""
Seed script for manual API testing. Run with:
    DATABASE_URL=... .venv/bin/python seed.py

Safe to run multiple times — uses natural keys to avoid duplicates.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.composer import Composer
from app.models.enums import PerformanceStatus, PerformerType
from app.models.performance import Performance
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry
from app.models.set_list_performer import SetListPerformer
from app.models.venue import Venue
from app.models.work import Work

engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(engine)


def upsert_composer(session, **kwargs) -> Composer:
    if kwargs.get("open_opus_id"):
        existing = session.query(Composer).where(Composer.open_opus_id == kwargs["open_opus_id"]).first()
        if existing:
            return existing
    obj = Composer(**kwargs)
    session.add(obj)
    session.flush()
    return obj


def upsert_performer(session, **kwargs) -> Performer:
    if kwargs.get("musicbrainz_id"):
        existing = session.query(Performer).where(Performer.musicbrainz_id == kwargs["musicbrainz_id"]).first()
        if existing:
            return existing
    obj = Performer(**kwargs)
    session.add(obj)
    session.flush()
    return obj


def upsert_venue(session, **kwargs) -> Venue:
    existing = (
        session.query(Venue)
        .where(Venue.osm_type == kwargs["osm_type"], Venue.osm_id == kwargs["osm_id"])
        .first()
    )
    if existing:
        return existing
    obj = Venue(**kwargs)
    session.add(obj)
    session.flush()
    return obj


def upsert_work(session, composers: list[Composer], **kwargs) -> Work:
    if kwargs.get("open_opus_id"):
        existing = session.query(Work).where(Work.open_opus_id == kwargs["open_opus_id"]).first()
        if existing:
            return existing
    obj = Work(**kwargs)
    obj.composers = composers
    session.add(obj)
    session.flush()
    return obj


def main():
    with Session() as session:
        print("Seeding composers...")
        beethoven = upsert_composer(
            session,
            name="Ludwig van Beethoven",
            sort_name="Beethoven, Ludwig van",
            open_opus_id="13",
        )
        brahms = upsert_composer(
            session,
            name="Johannes Brahms",
            sort_name="Brahms, Johannes",
            open_opus_id="14",
        )
        mahler = upsert_composer(
            session,
            name="Gustav Mahler",
            sort_name="Mahler, Gustav",
            open_opus_id="43",
        )

        print("Seeding performers...")
        berlin_phil = upsert_performer(
            session,
            name="Berlin Philharmonic",
            sort_name="Berlin Philharmonic",
            type=PerformerType.ORCHESTRA,
            musicbrainz_id="dea28aa9-1086-4ffa-8739-0ccc759de1ce",
        )
        rattle = upsert_performer(
            session,
            name="Simon Rattle",
            sort_name="Rattle, Simon",
            type=PerformerType.CONDUCTOR,
            musicbrainz_id="e4bd1c47-22e5-4afc-a8b2-a4e31878c0f5",
        )
        argerich = upsert_performer(
            session,
            name="Martha Argerich",
            sort_name="Argerich, Martha",
            type=PerformerType.SOLO,
            specialty="piano",
            musicbrainz_id="3c4bcb53-f08c-4bcc-89c0-e0d6c8a54a7c",
        )

        print("Seeding works...")
        beethoven_9 = upsert_work(
            session,
            composers=[beethoven],
            title="Symphony No. 9 in D minor",
            type="Symphony",
            key="D minor",
            catalog_number="Op. 125",
            open_opus_id="374",
        )
        brahms_piano_2 = upsert_work(
            session,
            composers=[brahms],
            title="Piano Concerto No. 2 in B-flat major",
            type="Concerto",
            key="B-flat major",
            catalog_number="Op. 83",
            open_opus_id="1090",
        )
        mahler_5 = upsert_work(
            session,
            composers=[mahler],
            title="Symphony No. 5 in C-sharp minor",
            type="Symphony",
            key="C-sharp minor",
            open_opus_id="1348",
        )

        print("Seeding venues...")
        philharmonie = upsert_venue(
            session,
            name="Berliner Philharmonie",
            city="Berlin",
            country="Germany",
            formatted_address="Herbert-von-Karajan-Straße 1, 10785 Berlin",
            website_uri="https://www.berliner-philharmoniker.de",
            osm_type="way",
            osm_id=26953440,
        )
        carnegie = upsert_venue(
            session,
            name="Carnegie Hall",
            city="New York",
            country="United States",
            formatted_address="881 7th Ave, New York, NY 10019",
            website_uri="https://www.carnegiehall.org",
            osm_type="way",
            osm_id=130568688,
        )

        print("Seeding performances...")

        perf1_exists = session.query(Performance).where(Performance.venue_id == philharmonie.id).first()
        if not perf1_exists:
            perf1 = Performance(
                date=datetime.fromisoformat("2026-06-16T00:30:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.UPCOMING,
                venue_id=philharmonie.id,
                conductor_id=rattle.id,
            )
            perf1.performers = [berlin_phil]
            session.add(perf1)
            session.flush()

            entry1 = SetListEntry(
                performance_id=perf1.id,
                work_id=mahler_5.id,
                order=1,
            )
            entry1.featured_performers = []
            session.add(entry1)

        perf2_exists = session.query(Performance).where(Performance.venue_id == carnegie.id).first()
        if not perf2_exists:
            perf2 = Performance(
                date=datetime.fromisoformat("2025-11-21T02:00:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.ATTENDED,
                venue_id=carnegie.id,
                conductor_id=rattle.id,
            )
            perf2.performers = [berlin_phil]
            session.add(perf2)
            session.flush()

            entry2 = SetListEntry(
                performance_id=perf2.id,
                work_id=brahms_piano_2.id,
                order=1,
                notes="Argerich was a late substitute",
            )
            entry2.featured_performers = [
                SetListPerformer(performer_id=argerich.id, role="piano")
            ]
            session.add(entry2)

            entry3 = SetListEntry(
                performance_id=perf2.id,
                work_id=beethoven_9.id,
                order=2,
            )
            entry3.featured_performers = []
            session.add(entry3)

        session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
