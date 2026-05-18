from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.venue import Venue, VenueCreate, VenueRead, VenueUpdate
from app.services import find_or_create_venue

router = APIRouter(prefix="/venues", tags=["venues"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[VenueRead])
def get_venues(session: SessionDep):
    return session.execute(select(Venue)).scalars().all()


@router.get("/{venue_id}", response_model=VenueRead)
def get_venue(venue_id: str, session: SessionDep):
    venue = session.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.post("/", response_model=VenueRead, status_code=201)
def create_venue(body: VenueCreate, session: SessionDep):
    venue = find_or_create_venue(body, session)
    session.commit()
    session.refresh(venue)
    return venue


@router.patch("/{venue_id}", response_model=VenueRead)
def update_venue(venue_id: str, body: VenueUpdate, session: SessionDep):
    venue = session.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(venue, field, value)
    session.commit()
    session.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=204)
def delete_venue(venue_id: str, session: SessionDep):
    venue = session.get(Venue, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    session.delete(venue)
    session.commit()
