from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models.user import User
from app.models.work import Work, WorkCreate, WorkRead, WorkUpdate
from app.auth import CurrentUserDep
from app.services import find_or_create_work

router = APIRouter(prefix="/works", tags=["works"])

SessionDep = Annotated[Session, Depends(get_session)]


def _visible(user: User):
    """A row is visible when it's global (ownerless) or owned by the caller."""
    return or_(Work.user_id.is_(None), Work.user_id == user.id)


@router.get("/", response_model=list[WorkRead])
def get_works(session: SessionDep, current_user: CurrentUserDep, name: str | None = None):
    query = (
        session.query(Work)
        .filter(_visible(current_user))
        .options(selectinload(Work.composers))
    )
    if name:
        query = query.filter(Work.title.ilike(f"%{name}%"))
    return session.scalars(query).all()


@router.get("/{work_id}", response_model=WorkRead)
def get_work(work_id: str, session: SessionDep, current_user: CurrentUserDep):
    work = session.scalars(
        session.query(Work)
        .where(Work.id == work_id, _visible(current_user))
        .options(selectinload(Work.composers))
    ).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work


@router.post("/", response_model=WorkRead, status_code=201)
def create_work(data: WorkCreate, session: SessionDep, current_user: CurrentUserDep):
    work = find_or_create_work(data, session, current_user.id)
    session.commit()
    session.refresh(work)
    return work
