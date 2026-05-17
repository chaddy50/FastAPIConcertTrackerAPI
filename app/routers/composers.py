from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.composer import Composer, ComposerCreate, ComposerRead, ComposerUpdate

router = APIRouter(prefix="/composers", tags=["composers"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[ComposerRead])
def get_composers(session: SessionDep):
    return session.query(Composer).all()


@router.get("/{composer_id}", response_model=ComposerRead)
def get_composer(composer_id: str, session: SessionDep):
    composer = session.get(Composer, composer_id)
    if not composer:
        raise HTTPException(status_code=404, detail="Composer not found")
    return composer


@router.post("/", response_model=ComposerRead, status_code=201)
def create_composer(data: ComposerCreate, session: SessionDep):
    if data.open_opus_id:
        existing = session.query(Composer).where(Composer.open_opus_id == data.open_opus_id).first()
        if existing:
            return existing

    composer = Composer(**data.model_dump())
    session.add(composer)
    session.commit()
    session.refresh(composer)
    return composer
