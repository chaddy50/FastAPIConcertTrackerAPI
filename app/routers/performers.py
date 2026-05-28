from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.performer import Performer, PerformerCreate, PerformerRead, PerformerUpdate
from app.services import find_or_create_performer

router = APIRouter(prefix="/performers", tags=["performers"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[PerformerRead])
def get_performers(session: SessionDep, name: str | None = None):
    query = session.query(Performer)
    if name:
        query = query.filter(Performer.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/{performer_id}", response_model=PerformerRead)
def get_performer(performer_id: str, session: SessionDep):
    performer = session.get(Performer, performer_id)
    if not performer:
        raise HTTPException(status_code=404, detail="Performer not found")
    return performer


@router.post("/", response_model=PerformerRead, status_code=201)
def create_performer(data: PerformerCreate, session: SessionDep):
    performer = find_or_create_performer(data, session)
    session.commit()
    session.refresh(performer)
    return performer
