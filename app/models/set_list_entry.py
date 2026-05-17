from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.performer import Performer, PerformerRead
from app.models.set_list_performer import SetListPerformer, SetListPerformerInput, SetListPerformerRead
from app.models.work import Work, WorkRead

if TYPE_CHECKING:
    from app.models.performance import Performance


class SetListEntry(Base):
    __tablename__ = "set_list_entry"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    order: Mapped[int]
    notes: Mapped[Optional[str]]
    performance_id: Mapped[str] = mapped_column(ForeignKey("performance.id"))
    work_id: Mapped[str] = mapped_column(ForeignKey("work.id"))
    conductor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("performer.id"))

    performance: Mapped[Performance] = relationship(back_populates="set_list")
    work: Mapped[Work] = relationship()
    conductor: Mapped[Optional[Performer]] = relationship()
    featured_performers: Mapped[list[SetListPerformer]] = relationship(
        back_populates="set_list_entry", cascade="all, delete-orphan"
    )


class SetListEntryCreate(Schema):
    performance_id: str
    work_id: str
    order: int
    notes: Optional[str] = None
    conductor_id: Optional[str] = None
    featured_performers: list[SetListPerformerInput]


class SetListEntryRead(ReadSchema):
    id: str
    order: int
    notes: Optional[str] = None
    work: WorkRead
    conductor: Optional[PerformerRead] = None
    featured_performers: list[SetListPerformerRead]


class SetListEntryUpdate(Schema):
    work_id: Optional[str] = None
    order: Optional[int] = None
    notes: Optional[str] = None
    conductor_id: Optional[str] = None
    featured_performers: Optional[list[SetListPerformerInput]] = None
