from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.client_supplied_id import ClientSuppliedId
from app.models.composer import Composer, ComposerCreate, ComposerRead

work_composer = Table(
    "work_composer",
    Base.metadata,
    Column("work_id", ForeignKey("work.id"), primary_key=True),
    Column("composer_id", ForeignKey("composer.id"), primary_key=True),
)


class Work(Base):
    __tablename__ = "work"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str]
    type: Mapped[Optional[str]]
    key: Mapped[Optional[str]]
    catalog_number: Mapped[Optional[str]]
    open_opus_id: Mapped[Optional[str]] = mapped_column(String, unique=True)

    composers: Mapped[list[Composer]] = relationship(secondary=work_composer, back_populates="works")


class WorkBase(Schema):
    title: str
    type: Optional[str] = None
    key: Optional[str] = None
    catalog_number: Optional[str] = None
    open_opus_id: Optional[str] = None


class WorkCreate(WorkBase):
    id: ClientSuppliedId = None
    composers: list[ComposerCreate]


class WorkRead(ReadSchema):
    id: str
    title: str
    type: Optional[str] = None
    key: Optional[str] = None
    catalog_number: Optional[str] = None
    open_opus_id: Optional[str] = None
    composers: list[ComposerRead]


class WorkUpdate(Schema):
    title: Optional[str] = None
    type: Optional[str] = None
    key: Optional[str] = None
    catalog_number: Optional[str] = None
    open_opus_id: Optional[str] = None
