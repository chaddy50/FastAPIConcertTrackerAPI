from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.performer import Performer, PerformerRead

if TYPE_CHECKING:
    from app.models.set_list_entry import SetListEntry


class SetListPerformer(Base):
    __tablename__ = "set_list_performer"

    set_list_entry_id: Mapped[str] = mapped_column(ForeignKey("set_list_entry.id"), primary_key=True)
    performer_id: Mapped[str] = mapped_column(ForeignKey("performer.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String)
    order: Mapped[int] = mapped_column(Integer)

    set_list_entry: Mapped[SetListEntry] = relationship(back_populates="featured_performers")
    performer: Mapped[Performer] = relationship()


class SetListPerformerInput(Schema):
    performer_id: str
    role: str
    order: int


class SetListPerformerRead(ReadSchema):
    performer: PerformerRead
    role: str
    order: int
