from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models.enums import PerformanceStatus
from app.models.performance import Performance, PerformanceCreate, PerformanceRead, PerformanceUpdate
from app.models.performer import Performer
from app.models.set_list_entry import SetListEntry
from app.models.set_list_performer import SetListPerformer
from app.models.venue import Venue
from app.models.work import Work

router = APIRouter(prefix="/performances", tags=["performances"])

SessionDep = Annotated[Session, Depends(get_session)]


def _load_performance(performance_id: str, session: Session) -> Performance:
    performance = session.scalars(
        session.query(Performance)
        .where(Performance.id == performance_id)
        .options(
            selectinload(Performance.venue),
            selectinload(Performance.performers),
            selectinload(Performance.set_list).selectinload(SetListEntry.work).selectinload(Work.composers),
            selectinload(Performance.set_list).selectinload(SetListEntry.featured_performers).selectinload(SetListPerformer.performer),
        )
    ).first()
    if not performance:
        raise HTTPException(status_code=404, detail="Performance not found")
    return performance


@router.get("/", response_model=list[PerformanceRead])
def get_performances(
    session: SessionDep,
    status: str | None = None,
    sort: Literal["date_asc", "date_desc"] = "date_asc",
    limit: Annotated[int | None, Query(gt=0)] = None,
    date_after: datetime | None = None,
):
    query = session.query(Performance).options(
        selectinload(Performance.venue),
        selectinload(Performance.performers),
        selectinload(Performance.set_list).selectinload(SetListEntry.work).selectinload(Work.composers),
        selectinload(Performance.set_list).selectinload(SetListEntry.featured_performers).selectinload(SetListPerformer.performer),
    )

    if status:
        statuses = []
        for raw in status.split(","):
            value = raw.strip()
            try:
                statuses.append(PerformanceStatus(value))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid status: {value}")
        query = query.filter(Performance.status.in_(statuses))

    if date_after is not None:
        query = query.filter(Performance.date > date_after)

    if sort == "date_desc":
        query = query.order_by(Performance.date.desc())
    else:
        query = query.order_by(Performance.date.asc())

    if limit is not None:
        query = query.limit(limit)

    return session.scalars(query).all()


@router.get("/{performance_id}", response_model=PerformanceRead)
def get_performance(performance_id: str, session: SessionDep):
    return _load_performance(performance_id, session)


@router.post("/", response_model=PerformanceRead, status_code=201)
def create_performance(data: PerformanceCreate, session: SessionDep):
    venue = session.get(Venue, data.venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    performers = []
    for performer_id in data.performer_ids:
        performer = session.get(Performer, performer_id)
        if not performer:
            raise HTTPException(status_code=404, detail=f"Performer {performer_id} not found")
        performers.append(performer)

    performance = Performance(
        date=data.date,
        status=data.status,
        venue_id=venue.id,
    )
    performance.performers = performers
    session.add(performance)
    session.flush()

    for entry_data in data.set_list:
        work = session.get(Work, entry_data.work_id)
        if not work:
            raise HTTPException(status_code=404, detail=f"Work {entry_data.work_id} not found")
        entry = SetListEntry(
            performance_id=performance.id,
            work_id=work.id,
            order=entry_data.order,
            notes=entry_data.notes,
        )
        entry.featured_performers = []
        for fp in entry_data.featured_performers:
            performer = session.get(Performer, fp.performer_id)
            if not performer:
                raise HTTPException(status_code=404, detail=f"Performer {fp.performer_id} not found")
            entry.featured_performers.append(
                SetListPerformer(performer_id=performer.id, role=fp.role)
            )
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
