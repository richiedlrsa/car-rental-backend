from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from db import SessionDep
from models import UserBase, Reservations, Cars
from user import get_current_user

router = APIRouter(prefix='user_info', tags=['user info'])

@router.get('/reservations')
async def get_reservations(db: SessionDep, status: str | None = None, cursor: int | None = None, limit: int | None = None, user: UserBase = Depends(get_current_user)):
    if not limit:
        limit = 20
        
    match status:
        case 'active':
            db_statuses = {'pending', 'active', 'confirmed'}
        case 'inactive':
            db_statuses = {'completed', 'cancelled'}
        case _:
            db_statuses = {'pending', 'active', 'confirmed', 'completed', 'cancelled'}
            
    condition = [Reservations.status.in_(db_statuses), Reservations.user_email == user.email]
    if cursor:
        condition.append(Reservations.id >= cursor)
    stmt = select(Reservations, Cars).where(*condition).join(Cars).order_by(Reservations.id).limit(limit + 1)
    results = db.exec(stmt).all()
    if not results:
        return {'response': f'No {status if status != 'all' else 'found'} reservations'}
    reservations_resp = []
    for res, car in results:
        car_info = {'id': car.id, 'make': car.make, 'model': car.model, 'year': car.year}
        reservation = res.model_dump(exclude={'car_id', 'created_at'})
        reservation['car'] = car_info
        reservations_resp.append(reservation)
    
    if len(reservations_resp) > limit:
        cursor = reservations_resp.pop()['id']
    else:
        cursor = None
        
    return {'items': reservations_resp, 'next_cursor': cursor}

@router.patch("/reservations/cancel/{id}")
def cancel_reservation(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    reservation = db.exec(select(Reservations).where(Reservations.id == id, Reservations.user_email == user.email)).first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

    if reservation.status not in {'pending', 'cancelled'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Cannot cancel a reservation with status {reservation.status}')
    setattr(reservation, 'status', 'cancelled')
        
    db.add(reservation)
    db.commit()
    
    return {'detail': 'Reservation successfully updated'}