from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.performer import Performer, PerformerCreate, PerformerRead, PerformerUpdate
from app.models.user import User
from app.auth import CurrentUserDep
from app.services import find_or_create_performer

router = APIRouter(prefix="/performers", tags=["performers"])

SessionDep = Annotated[Session, Depends(get_session)]


def _visible(user: User):
    """A row is visible when it's global (ownerless) or owned by the caller."""
    return or_(Performer.user_id.is_(None), Performer.user_id == user.id)


@router.get("/", response_model=list[PerformerRead])
def get_performers(session: SessionDep, current_user: CurrentUserDep, name: str | None = None):
    query = session.query(Performer).filter(_visible(current_user))
    if name:
        query = query.filter(Performer.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{performer_id}", response_model=PerformerRead)
def get_performer(performer_id: str, session: SessionDep, current_user: CurrentUserDep):
    performer = session.scalars(
        session.query(Performer).where(Performer.id == performer_id, _visible(current_user))
    ).first()
    if not performer:
        raise HTTPException(status_code=404, detail="Performer not found")
    return performer


@router.post("/", response_model=PerformerRead, status_code=201)
def create_performer(data: PerformerCreate, session: SessionDep, current_user: CurrentUserDep):
    performer = find_or_create_performer(data, session, current_user.id)
    session.commit()
    session.refresh(performer)
    return performer
