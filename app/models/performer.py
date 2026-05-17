from typing import Optional
from uuid import uuid4

from sqlalchemy import Enum as SaEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base
from app.models.base_schema import ReadSchema, Schema
from app.models.enums import PerformerType


class Performer(Base):
    __tablename__ = "performer"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str]
    sort_name: Mapped[Optional[str]]
    type: Mapped[PerformerType] = mapped_column(SaEnum(PerformerType))
    specialty: Mapped[Optional[str]]
    musicbrainz_id: Mapped[Optional[str]] = mapped_column(String, unique=True)


class PerformerBase(Schema):
    name: str
    sort_name: Optional[str] = None
    type: PerformerType
    specialty: Optional[str] = None
    musicbrainz_id: Optional[str] = None


class PerformerCreate(PerformerBase):
    pass


class PerformerRead(ReadSchema):
    id: str
    name: str
    sort_name: Optional[str] = None
    type: PerformerType
    specialty: Optional[str] = None
    musicbrainz_id: Optional[str] = None


class PerformerUpdate(Schema):
    name: Optional[str] = None
    sort_name: Optional[str] = None
    type: Optional[PerformerType] = None
    specialty: Optional[str] = None
    musicbrainz_id: Optional[str] = None
