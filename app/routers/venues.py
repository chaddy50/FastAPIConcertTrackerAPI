from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.user import User
from app.models.venue import Venue, VenueCreate, VenueRead, VenueUpdate
from app.auth import CurrentUserDep
from app.services import find_or_create_venue

router = APIRouter(prefix="/venues", tags=["venues"])

SessionDep = Annotated[Session, Depends(get_session)]


def _visible(user: User):
    """A row is visible when it's global (ownerless) or owned by the caller."""
    return or_(Venue.user_id.is_(None), Venue.user_id == user.id)


@router.get("/", response_model=list[VenueRead])
def get_venues(session: SessionDep, current_user: CurrentUserDep):
    return session.execute(select(Venue).where(_visible(current_user))).scalars().all()


@router.get("/{venue_id}", response_model=VenueRead)
def get_venue(venue_id: str, session: SessionDep, current_user: CurrentUserDep):
    venue = session.scalars(
        select(Venue).where(Venue.id == venue_id, _visible(current_user))
    ).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.post("/", response_model=VenueRead, status_code=201)
def create_venue(body: VenueCreate, session: SessionDep, current_user: CurrentUserDep):
    venue = find_or_create_venue(body, session, current_user.id)
    session.commit()
    session.refresh(venue)
    return venue


@router.patch("/{venue_id}", response_model=VenueRead)
def update_venue(venue_id: str, body: VenueUpdate, session: SessionDep, current_user: CurrentUserDep):
    venue = session.scalars(
        select(Venue).where(Venue.id == venue_id, _visible(current_user))
    ).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(venue, field, value)
    session.commit()
    session.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=204)
def delete_venue(venue_id: str, session: SessionDep, current_user: CurrentUserDep):
    venue = session.scalars(
        select(Venue).where(Venue.id == venue_id, _visible(current_user))
    ).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    session.delete(venue)
    session.commit()
