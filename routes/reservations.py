from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, exists
from db import SessionDep
from models import ReservationBase, Reservations

router = APIRouter(prefix='/reservations', tags=['reservations'])

@router.post("/add")
async def add_reservation(db: SessionDep, reservation: ReservationBase):
    overlap_condition = and_(
        Reservations.start_at <= reservation.end_at,
        Reservations.end_at >= reservation.start_at,
        Reservations.status.in_({'pending', 'confirmed', 'active'}),
        Reservations.car_id == reservation.car_id
    )

    conflict_exists = db.exec(select(exists().where(overlap_condition))).first()
    
    if conflict_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected car is not available for these dates.")
    
    db_reservation = Reservations(**reservation.model_dump())
    try:
        db.add(db_reservation)
        db.commit()
    except IntegrityError:
       raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected car is not available for these dates.") 

    return {"success": "reservation successfully added"}