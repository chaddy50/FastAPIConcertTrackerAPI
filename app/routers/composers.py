from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.composer import Composer, ComposerCreate, ComposerRead, ComposerUpdate
from app.models.user import User
from app.auth import CurrentUserDep
from app.services import find_or_create_composer

router = APIRouter(prefix="/composers", tags=["composers"])

SessionDep = Annotated[Session, Depends(get_session)]


def _visible(user: User):
    """A row is visible when it's global (ownerless) or owned by the caller."""
    return or_(Composer.user_id.is_(None), Composer.user_id == user.id)


@router.get("/", response_model=list[ComposerRead])
def get_composers(session: SessionDep, current_user: CurrentUserDep, name: str | None = None):
    query = session.query(Composer).filter(_visible(current_user))
    if name:
        query = query.filter(Composer.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{composer_id}", response_model=ComposerRead)
def get_composer(composer_id: str, session: SessionDep, current_user: CurrentUserDep):
    composer = session.scalars(
        session.query(Composer).where(Composer.id == composer_id, _visible(current_user))
    ).first()
    if not composer:
        raise HTTPException(status_code=404, detail="Composer not found")
    return composer


@router.post("/", response_model=ComposerRead, status_code=201)
def create_composer(data: ComposerCreate, session: SessionDep, current_user: CurrentUserDep):
    composer = find_or_create_composer(data, session, current_user.id)
    session.commit()
    session.refresh(composer)
    return composer
