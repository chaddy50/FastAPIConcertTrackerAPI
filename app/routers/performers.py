from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.performer import Performer, PerformerCreate, PerformerRead, PerformerUpdate

router = APIRouter(prefix="/performers", tags=["performers"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[PerformerRead])
def get_performers(session: SessionDep):
    return session.query(Performer).all()


@router.get("/{performer_id}", response_model=PerformerRead)
def get_performer(performer_id: str, session: SessionDep):
    performer = session.get(Performer, performer_id)
    if not performer:
        raise HTTPException(status_code=404, detail="Performer not found")
    return performer


@router.post("/", response_model=PerformerRead, status_code=201)
def create_performer(data: PerformerCreate, session: SessionDep):
    if data.musicbrainz_id:
        existing = session.query(Performer).where(Performer.musicbrainz_id == data.musicbrainz_id).first()
        if existing:
            return existing

    performer = Performer(**data.model_dump())
    session.add(performer)
    session.commit()
    session.refresh(performer)
    return performer
