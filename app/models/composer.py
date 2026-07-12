from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.client_supplied_id import ClientSuppliedId

if TYPE_CHECKING:
    from app.models.work import Work


class Composer(Base):
    __tablename__ = "composer"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str]
    sort_name: Mapped[Optional[str]]
    open_opus_id: Mapped[Optional[str]] = mapped_column(String, unique=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("user.id"), nullable=True, index=True)

    works: Mapped[list[Work]] = relationship(secondary="work_composer", back_populates="composers")


class ComposerBase(Schema):
    name: str
    sort_name: Optional[str] = None
    open_opus_id: Optional[str] = None


class ComposerCreate(ComposerBase):
    id: ClientSuppliedId = None


class ComposerRead(ReadSchema):
    id: str
    name: str
    sort_name: Optional[str] = None
    open_opus_id: Optional[str] = None


class ComposerUpdate(Schema):
    name: Optional[str] = None
    sort_name: Optional[str] = None
    open_opus_id: Optional[str] = None
