from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SaEnum, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.client_supplied_id import ClientSuppliedId
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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[PerformanceStatus] = mapped_column(
        SaEnum(PerformanceStatus), default=PerformanceStatus.UPCOMING
    )
    venue_id: Mapped[str] = mapped_column(ForeignKey("venue.id"))
    notes: Mapped[Optional[str]]

    venue: Mapped[Venue] = relationship()
    performers: Mapped[list[Performer]] = relationship(secondary=performance_performer)
    set_list: Mapped[list[SetListEntry]] = relationship(back_populates="performance", cascade="all, delete-orphan")


class FeaturedPerformerInput(Schema):
    performer_id: str
    role: Optional[str] = None


class SetListEntryInput(Schema):
    id: ClientSuppliedId = None
    order: int
    notes: Optional[str] = None
    work_id: str
    featured_performers: list[FeaturedPerformerInput] = []


class PerformanceCreate(Schema):
    id: ClientSuppliedId = None
    date: datetime
    status: PerformanceStatus = PerformanceStatus.UPCOMING
    venue_id: str
    notes: Optional[str] = None
    performer_ids: list[str] = []
    set_list: list[SetListEntryInput] = []


class PerformanceRead(ReadSchema):
    id: str
    date: datetime
    status: PerformanceStatus
    venue: VenueRead
    notes: Optional[str] = None
    performers: list[PerformerRead]
    set_list: list[SetListEntryRead] = []


class PerformanceUpdate(Schema):
    date: Optional[datetime] = None
    status: Optional[PerformanceStatus] = None
    venue_id: Optional[str] = None
    notes: Optional[str] = None
    performer_ids: Optional[list[str]] = None
