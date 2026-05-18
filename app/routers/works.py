from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models.work import Work, WorkCreate, WorkRead, WorkUpdate
from app.services import find_or_create_work

router = APIRouter(prefix="/works", tags=["works"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[WorkRead])
def get_works(session: SessionDep):
    return session.scalars(
        session.query(Work).options(selectinload(Work.composers))
    ).all()


@router.get("/{work_id}", response_model=WorkRead)
def get_work(work_id: str, session: SessionDep):
    work = session.scalars(
        session.query(Work).where(Work.id == work_id).options(selectinload(Work.composers))
    ).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work


@router.post("/", response_model=WorkRead, status_code=201)
def create_work(data: WorkCreate, session: SessionDep):
    work = find_or_create_work(data, session)
    session.commit()
    session.refresh(work)
    return work
