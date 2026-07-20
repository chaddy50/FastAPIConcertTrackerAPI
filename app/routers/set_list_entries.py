from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models.performance import Performance
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry, SetListEntryCreate, SetListEntryRead, SetListEntryUpdate
from app.models.set_list_performer import SetListPerformer, SetListPerformerInput
from app.models.work import Work

router = APIRouter(prefix="/set-list-entries", tags=["set-list-entries"])

SessionDep = Annotated[Session, Depends(get_session)]


def _load_set_list_entry(entry_id: str, session: Session) -> SetListEntry:
    entry = session.scalars(
        session.query(SetListEntry)
        .where(SetListEntry.id == entry_id)
        .options(
            selectinload(SetListEntry.work).selectinload(Work.composers),
            selectinload(SetListEntry.featured_performers).selectinload(SetListPerformer.performer),
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Set list entry not found")
    return entry


def _build_featured_performers(inputs: list[SetListPerformerInput], session: Session) -> list[SetListPerformer]:
    result = []
    for item in inputs:
        if not session.get(Performer, item.performer_id):
            raise HTTPException(status_code=404, detail=f"Performer {item.performer_id} not found")
        result.append(SetListPerformer(performer_id=item.performer_id, role=item.role, order=item.order))
    return result


@router.post("/", response_model=SetListEntryRead, status_code=201)
def create_set_list_entry(data: SetListEntryCreate, session: SessionDep):
    if not session.get(Performance, data.performance_id):
        raise HTTPException(status_code=404, detail="Performance not found")
    if not session.get(Work, data.work_id):
        raise HTTPException(status_code=404, detail="Work not found")
    if data.id is not None and session.get(SetListEntry, data.id):
        raise HTTPException(status_code=409, detail=f"Set list entry {data.id} already exists")

    dumped = data.model_dump(exclude={"featured_performers"})
    if dumped.get("id") is None:
        dumped.pop("id", None)  # let default=lambda: str(uuid4()) apply
    entry = SetListEntry(**dumped)
    entry.featured_performers = _build_featured_performers(data.featured_performers, session)
    session.add(entry)
    session.commit()
    return _load_set_list_entry(entry.id, session)


@router.put("/{entry_id}", response_model=SetListEntryRead)
def update_set_list_entry(entry_id: str, data: SetListEntryUpdate, session: SessionDep):
    entry = _load_set_list_entry(entry_id, session)

    update_data = data.model_dump(exclude_unset=True)
    featured_performers_input = update_data.pop("featured_performers", None)

    for field, value in update_data.items():
        if field == "work_id" and not session.get(Work, value):
            raise HTTPException(status_code=404, detail="Work not found")
        setattr(entry, field, value)

    if featured_performers_input is not None:
        # model_dump converts nested Pydantic objects to dicts — reconstruct before validation.
        # Reassigning the list lets cascade="all, delete-orphan" clean up the old rows automatically.
        entry.featured_performers = _build_featured_performers(
            [SetListPerformerInput(**d) for d in featured_performers_input], session
        )

    session.commit()
    return _load_set_list_entry(entry.id, session)


@router.delete("/{entry_id}", status_code=204)
def delete_set_list_entry(entry_id: str, session: SessionDep):
    entry = session.get(SetListEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Set list entry not found")
    session.delete(entry)
    session.commit()
