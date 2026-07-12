"""
Seed script for manual API testing. Run as a module from the repo root
(so `app` is importable):
    DATABASE_URL=... .venv/bin/python -m scripts.seed

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
from app.models.user import User
from app.models.venue import Venue
from app.models.work import Work
from app.auth import generate_api_key, hash_api_key

engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(engine)


def upsert_user(session, username: str) -> User:
    """Find-or-create the seed user. On first creation, prints a usable API key
    (the personal log is now per-user, so the seeded performances need an owner)."""
    existing = session.query(User).where(User.username == username).first()
    if existing:
        return existing
    key = generate_api_key()
    user = User(username=username, api_key_hash=hash_api_key(key))
    session.add(user)
    session.flush()
    print(f"Created seed user {username!r}. API key (shown once): {key}")
    return user


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
        print("Seeding user...")
        seed_user = upsert_user(session, "seed")

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
            specialty="conductor",
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
        musikverein = upsert_venue(
            session,
            name="Musikverein",
            city="Vienna",
            country="Austria",
            formatted_address="Musikvereinsplatz 1, 1010 Wien",
            website_uri="https://www.musikverein.at",
            osm_type="way",
            osm_id=29812613,
        )
        symphony_center = upsert_venue(
            session,
            name="Symphony Center",
            city="Chicago",
            country="United States",
            formatted_address="220 S Michigan Ave, Chicago, IL 60604",
            website_uri="https://www.cso.org",
            osm_type="way",
            osm_id=151991390,
        )
        royal_albert = upsert_venue(
            session,
            name="Royal Albert Hall",
            city="London",
            country="United Kingdom",
            formatted_address="Kensington Gore, London SW7 2AP",
            website_uri="https://www.royalalberthall.com",
            osm_type="way",
            osm_id=23618837,
        )

        print("Seeding performances...")

        perf1_exists = session.query(Performance).where(Performance.venue_id == philharmonie.id).first()
        if not perf1_exists:
            perf1 = Performance(
                date=datetime.fromisoformat("2026-06-16T00:30:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.UPCOMING,
                venue_id=philharmonie.id,
                user_id=seed_user.id,
            )
            perf1.performers = [rattle, berlin_phil]
            session.add(perf1)
            session.flush()

            entry1 = SetListEntry(
                performance_id=perf1.id,
                user_id=seed_user.id,
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
                user_id=seed_user.id,
            )
            perf2.performers = [rattle, berlin_phil]
            session.add(perf2)
            session.flush()

            entry2 = SetListEntry(
                performance_id=perf2.id,
                user_id=seed_user.id,
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
                user_id=seed_user.id,
                work_id=beethoven_9.id,
                order=2,
            )
            entry3.featured_performers = []
            session.add(entry3)

        perf3_exists = session.query(Performance).where(Performance.venue_id == musikverein.id).first()
        if not perf3_exists:
            perf3 = Performance(
                date=datetime.fromisoformat("2025-04-05T19:30:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.ATTENDED,
                venue_id=musikverein.id,
                user_id=seed_user.id,
            )
            perf3.performers = [berlin_phil]
            session.add(perf3)
            session.flush()

            entry4 = SetListEntry(
                performance_id=perf3.id,
                user_id=seed_user.id,
                work_id=beethoven_9.id,
                order=1,
            )
            entry4.featured_performers = []
            session.add(entry4)

        perf4_exists = session.query(Performance).where(Performance.venue_id == symphony_center.id).first()
        if not perf4_exists:
            perf4 = Performance(
                date=datetime.fromisoformat("2026-02-14T20:00:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.ATTENDED,
                venue_id=symphony_center.id,
                user_id=seed_user.id,
            )
            perf4.performers = [rattle, berlin_phil]
            session.add(perf4)
            session.flush()

            entry5 = SetListEntry(
                performance_id=perf4.id,
                user_id=seed_user.id,
                work_id=mahler_5.id,
                order=1,
            )
            entry5.featured_performers = []
            session.add(entry5)

        perf5_exists = session.query(Performance).where(Performance.venue_id == royal_albert.id).first()
        if not perf5_exists:
            perf5 = Performance(
                date=datetime.fromisoformat("2026-09-12T19:00:00").replace(tzinfo=timezone.utc),
                status=PerformanceStatus.UPCOMING,
                venue_id=royal_albert.id,
                user_id=seed_user.id,
            )
            perf5.performers = [argerich, berlin_phil]
            session.add(perf5)
            session.flush()

            entry6 = SetListEntry(
                performance_id=perf5.id,
                user_id=seed_user.id,
                work_id=brahms_piano_2.id,
                order=1,
            )
            entry6.featured_performers = [
                SetListPerformer(performer_id=argerich.id, role="piano")
            ]
            session.add(entry6)

        session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
