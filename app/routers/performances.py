from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models.performance import Performance, PerformanceCreate, PerformanceRead, PerformanceUpdate
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry
from app.models.set_list_performer import SetListPerformer
from app.models.venue import Venue
from app.models.work import Work
from app.services import find_or_create_performer, find_or_create_venue, find_or_create_work

router = APIRouter(prefix="/performances", tags=["performances"])

SessionDep = Annotated[Session, Depends(get_session)]


def _load_performance(performance_id: str, session: Session) -> Performance:
    performance = session.scalars(
        session.query(Performance)
        .where(Performance.id == performance_id)
        .options(
            selectinload(Performance.venue),
            selectinload(Performance.performers),
            selectinload(Performance.conductor),
            selectinload(Performance.set_list).selectinload(SetListEntry.work).selectinload(Work.composers),
            selectinload(Performance.set_list).selectinload(SetListEntry.conductor),
            selectinload(Performance.set_list).selectinload(SetListEntry.featured_performers).selectinload(SetListPerformer.performer),
        )
    ).first()
    if not performance:
        raise HTTPException(status_code=404, detail="Performance not found")
    return performance


@router.get("/", response_model=list[PerformanceRead])
def get_performances(session: SessionDep):
    return session.scalars(
        session.query(Performance)
        .order_by(Performance.date.desc())
        .options(
            selectinload(Performance.venue),
            selectinload(Performance.performers),
            selectinload(Performance.conductor),
            selectinload(Performance.set_list).selectinload(SetListEntry.work).selectinload(Work.composers),
            selectinload(Performance.set_list).selectinload(SetListEntry.conductor),
            selectinload(Performance.set_list).selectinload(SetListEntry.featured_performers).selectinload(SetListPerformer.performer),
        )
    ).all()


@router.get("/{performance_id}", response_model=PerformanceRead)
def get_performance(performance_id: str, session: SessionDep):
    return _load_performance(performance_id, session)


@router.post("/", response_model=PerformanceRead, status_code=201)
def create_performance(data: PerformanceCreate, session: SessionDep):
    venue = find_or_create_venue(data.venue, session)
    conductor = find_or_create_performer(data.conductor, session) if data.conductor else None
    performers = [find_or_create_performer(p, session) for p in data.performers]

    performance = Performance(
        date=data.date,
        status=data.status,
        venue_id=venue.id,
        conductor_id=conductor.id if conductor else None,
    )
    performance.performers = performers
    session.add(performance)
    session.flush()

    for entry_data in data.set_list:
        work = find_or_create_work(entry_data.work, session)
        guest_conductor = find_or_create_performer(entry_data.conductor, session) if entry_data.conductor else None
        entry = SetListEntry(
            performance_id=performance.id,
            work_id=work.id,
            order=entry_data.order,
            notes=entry_data.notes,
            conductor_id=guest_conductor.id if guest_conductor else None,
        )
        entry.featured_performers = [
            SetListPerformer(
                performer_id=find_or_create_performer(fp.performer, session).id,
                role=fp.role,
            )
            for fp in entry_data.featured_performers
        ]
        session.add(entry)

    session.commit()
    return _load_performance(performance.id, session)


@router.put("/{performance_id}", response_model=PerformanceRead)
def update_performance(performance_id: str, data: PerformanceUpdate, session: SessionDep):
    performance = _load_performance(performance_id, session)

    # Only fields the client actually sent are in this dict — omitted fields are excluded,
    # so we don't accidentally overwrite existing values with None.
    update_data = data.model_dump(exclude_unset=True)
    performer_ids = update_data.pop("performer_ids", None)

    for field, value in update_data.items():
        if field == "venue_id" and not session.get(Venue, value):
            raise HTTPException(status_code=404, detail="Venue not found")
        if field == "conductor_id" and value and not session.get(Performer, value):
            raise HTTPException(status_code=404, detail="Conductor not found")
        setattr(performance, field, value)

    if performer_ids is not None:
        resolved = []
        for performer_id in performer_ids:
            performer = session.get(Performer, performer_id)
            if not performer:
                raise HTTPException(status_code=404, detail=f"Performer {performer_id} not found")
            resolved.append(performer)
        performance.performers = resolved

    session.commit()
    return _load_performance(performance.id, session)


@router.delete("/{performance_id}", status_code=204)
def delete_performance(performance_id: str, session: SessionDep):
    performance = session.get(Performance, performance_id)
    if not performance:
        raise HTTPException(status_code=404, detail="Performance not found")
    session.delete(performance)
    session.commit()
