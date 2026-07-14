"""
Stage 3: seed the database from concerts.json + catalog.json.

Usage:
    DATABASE_URL=postgresql+psycopg2://... python -m seeding.seed_from_catalog

Idempotent: reference entities are deduped by their external id when present
(open_opus_id / musicbrainz_id / osm), and by name when custom (null id).
Performances are deduped by (date, venue). Safe to run repeatedly.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.composer import Composer
from app.models.enums import PerformanceStatus, PerformerType
from app.models.performance import Performance
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry
from app.models.set_list_performer import SetListPerformer
from app.models.venue import Venue
from app.models.work import Work

# Notes record only a date, not a start time; assume a 19:30 local start and
# convert to UTC using the venue's timezone (DST-aware across 2024-2026).
PLACEHOLDER_LOCAL_TIME = (19, 30)  # (hour, minute)
DEFAULT_TZ = ZoneInfo("America/Chicago")
UK_TZ = ZoneInfo("Europe/London")


def tz_for_venue(venue: Venue) -> ZoneInfo:
    country = (venue.country or "").lower()
    city = (venue.city or "").lower()
    if "united kingdom" in country or "england" in country or "london" in city:
        return UK_TZ
    return DEFAULT_TZ


def performance_datetime(date_str: str, venue: Venue) -> datetime:
    hour, minute = PLACEHOLDER_LOCAL_TIME
    local = datetime.fromisoformat(date_str).replace(hour=hour, minute=minute, tzinfo=tz_for_venue(venue))
    return local.astimezone(timezone.utc)


class Seeder:
    def __init__(self, session: Session, catalog: dict):
        self.session = session
        self.catalog = catalog
        self.composers: dict[str, Composer] = {}
        self.works: dict[str, Work] = {}
        self.performers: dict[str, Performer] = {}
        self.venues: dict[str, Venue] = {}

    # -- reference entities ------------------------------------------------- #
    def composer(self, raw: str) -> Composer:
        if raw in self.composers:
            return self.composers[raw]
        d = self.catalog["composers"][raw]
        obj = None
        if d["open_opus_id"]:
            obj = self.session.query(Composer).filter_by(open_opus_id=d["open_opus_id"]).first()
        else:
            obj = self.session.query(Composer).filter_by(name=d["name"], open_opus_id=None).first()
        if obj is None:
            obj = Composer(name=d["name"], sort_name=d["sort_name"], open_opus_id=d["open_opus_id"])
            self.session.add(obj)
            self.session.flush()
        self.composers[raw] = obj
        return obj

    def work(self, composer_raw: str, title_raw: str) -> Work | None:
        key = f"{composer_raw}||{title_raw}"
        if key not in self.catalog["works"]:
            return None  # placeholder / skipped during resolve
        if key in self.works:
            return self.works[key]
        d = self.catalog["works"][key]
        composer = self.composer(d["composer_ref"])
        obj = None
        if d["open_opus_id"]:
            obj = self.session.query(Work).filter_by(open_opus_id=d["open_opus_id"]).first()
        else:
            obj = self.session.query(Work).filter_by(title=d["title"], open_opus_id=None).first()
        if obj is None:
            obj = Work(
                title=d["title"],
                type=d["type"],
                key=d["key"],
                catalog_number=d["catalog_number"],
                open_opus_id=d["open_opus_id"],
            )
            obj.composers = [composer]
            self.session.add(obj)
            self.session.flush()
        elif composer not in obj.composers:
            obj.composers.append(composer)
        self.works[key] = obj
        return obj

    def performer(self, raw: str) -> Performer | None:
        if raw not in self.catalog["performers"]:
            return None
        if raw in self.performers:
            return self.performers[raw]
        d = self.catalog["performers"][raw]
        obj = None
        if d["musicbrainz_id"]:
            obj = self.session.query(Performer).filter_by(musicbrainz_id=d["musicbrainz_id"]).first()
        else:
            obj = self.session.query(Performer).filter_by(name=d["name"], musicbrainz_id=None).first()
        if obj is None:
            obj = Performer(
                name=d["name"],
                sort_name=d["sort_name"],
                type=PerformerType(d["type"]),
                specialty=d["specialty"],
                musicbrainz_id=d["musicbrainz_id"],
            )
            self.session.add(obj)
            self.session.flush()
        self.performers[raw] = obj
        return obj

    def venue(self, key: str) -> Venue:
        if key in self.venues:
            return self.venues[key]
        d = self.catalog["venues"][key]
        obj = None
        if d["osm_type"] and d["osm_id"]:
            obj = self.session.query(Venue).filter_by(osm_type=d["osm_type"], osm_id=d["osm_id"]).first()
        else:
            obj = self.session.query(Venue).filter_by(name=d["name"], city=d["city"], osm_id=None).first()
        if obj is None:
            obj = Venue(
                name=d["name"],
                city=d["city"],
                country=d["country"],
                formatted_address=d["formatted_address"],
                website_uri=d["website_uri"],
                osm_type=d["osm_type"],
                osm_id=d["osm_id"],
            )
            self.session.add(obj)
            self.session.flush()
        self.venues[key] = obj
        return obj

    # -- performances ------------------------------------------------------- #
    def performance(self, concert: dict) -> None:
        binding = self.catalog["concert_bindings"].get(concert["source_file"])
        if not binding:
            print(f"  ! no binding for {concert['source_file']} -- did you run resolve.py? skipping")
            return
        venue = self.venue(binding["venue_ref"])
        when = performance_datetime(concert["date"], venue)

        existing = self.session.query(Performance).filter_by(date=when, venue_id=venue.id).first()
        if existing:
            print(f"  = {concert['source_file']} already seeded")
            return

        perf = Performance(
            date=when,
            status=PerformanceStatus(concert["status"] or "ATTENDED"),
            venue_id=venue.id,
        )
        perf.performers = [p for ref in binding["performer_refs"] if (p := self.performer(ref))]
        self.session.add(perf)
        self.session.flush()

        order = 0
        for entry in concert["set_list"]:
            work = self.work(entry["composer"], entry["work_title"])
            if work is None:
                continue
            order += 1
            sle = SetListEntry(
                performance_id=perf.id, work_id=work.id, order=order, notes=entry.get("notes")
            )
            if entry.get("soloist") and (sol := self.performer(entry["soloist"])):
                sle.featured_performers = [
                    SetListPerformer(performer_id=sol.id, role=sol.specialty or "soloist")
                ]
            self.session.add(sle)

        for extra in binding.get("extra_entries", []):
            work = self.work(extra["composer"], extra["work_title"])
            if work is None:
                continue
            order += 1
            sle = SetListEntry(
                performance_id=perf.id, work_id=work.id, order=order, notes="(encore)"
            )
            if extra.get("soloist") and (sol := self.performer(extra["soloist"])):
                sle.featured_performers = [
                    SetListPerformer(performer_id=sol.id, role=sol.specialty or "soloist")
                ]
            self.session.add(sle)

        print(f"  + seeded {concert['source_file']} ({order} works)")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    concerts = json.loads((repo_root / "seeding" / "concerts.json").read_text(encoding="utf-8"))["concerts"]
    catalog = json.loads((repo_root / "seeding" / "catalog.json").read_text(encoding="utf-8"))

    engine = create_engine(os.environ["DATABASE_URL"])
    with sessionmaker(engine)() as session:
        seeder = Seeder(session, catalog)
        print(f"Seeding {len(concerts)} concerts...")
        for concert in concerts:
            seeder.performance(concert)
        session.commit()
    print("Done.")


if __name__ == "__main__":
    main()
