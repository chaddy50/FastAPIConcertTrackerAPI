from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, Enum as SaEnum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.enums import PerformanceStatus
from app.models.performer import Performer, PerformerRead
from app.models.set_list_entry import SetListEntry, SetListEntryRead
from app.models.venue import Venue, VenueRead

performance_performer = Table(
    "performance_performer",
    Base.metadata,
    Column("performance_id", ForeignKey("performance.id"), primary_key=True),
    Column("performer_id", ForeignKey("performer.id"), primary_key=True),
)


class Performance(Base):
    __tablename__ = "performance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    date: Mapped[datetime]
    status: Mapped[PerformanceStatus] = mapped_column(
        SaEnum(PerformanceStatus), default=PerformanceStatus.UPCOMING
    )
    venue_id: Mapped[str] = mapped_column(ForeignKey("venue.id"))
    conductor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("performer.id"))

    venue: Mapped[Venue] = relationship()
    conductor: Mapped[Optional[Performer]] = relationship(foreign_keys="[Performance.conductor_id]")
    performers: Mapped[list[Performer]] = relationship(secondary=performance_performer)
    set_list: Mapped[list[SetListEntry]] = relationship(back_populates="performance")


class PerformanceCreate(Schema):
    date: datetime
    status: PerformanceStatus = PerformanceStatus.UPCOMING
    venue_id: str
    conductor_id: Optional[str] = None
    performer_ids: list[str]


class PerformanceRead(ReadSchema):
    id: str
    date: datetime
    status: PerformanceStatus
    venue: VenueRead
    performers: list[PerformerRead]
    conductor: Optional[PerformerRead] = None
    set_list: list[SetListEntryRead] = []


class PerformanceUpdate(Schema):
    date: Optional[datetime] = None
    status: Optional[PerformanceStatus] = None
    venue_id: Optional[str] = None
    performer_ids: Optional[list[str]] = None
    conductor_id: Optional[str] = None
