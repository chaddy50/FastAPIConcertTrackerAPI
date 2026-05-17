from typing import Annotated, Optional
from uuid import uuid4

from pydantic import BeforeValidator
from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base
from app.models.base_schema import ReadSchema, Schema

OsmId = Annotated[str, BeforeValidator(str)]


class Venue(Base):
    __tablename__ = "venue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[Optional[str]]
    city: Mapped[Optional[str]]
    country: Mapped[Optional[str]]
    formatted_address: Mapped[Optional[str]]
    website_uri: Mapped[Optional[str]]
    osm_type: Mapped[str]
    osm_id: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint("osm_type", "osm_id", name="uq_venue_osm"),
    )


class VenueBase(Schema):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    formatted_address: Optional[str] = None
    website_uri: Optional[str] = None
    osm_type: str
    osm_id: int


class VenueCreate(VenueBase):
    pass


class VenueRead(ReadSchema):
    id: str
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    formatted_address: Optional[str] = None
    website_uri: Optional[str] = None
    osm_type: str
    osm_id: OsmId  # coerced from BigInt to string for JSON compatibility


class VenueUpdate(Schema):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    formatted_address: Optional[str] = None
    website_uri: Optional[str] = None
    osm_type: Optional[str] = None
    osm_id: Optional[int] = None
