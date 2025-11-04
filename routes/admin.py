from fastapi import APIRouter, Depends, HTTPException, status 
from sqlmodel import select
from sqlalchemy import func
from db import SessionDep
from user import get_current_user
from models import Reservations, UserBase, Cars, CarImages

router = APIRouter(prefix='/admin', tags=['admin'])

@router.get("/reservation_counts")
async def get_reservation_counts(db: SessionDep, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
    
    active_reservations = db.exec(select(func.count()).select_from(Reservations).where(Reservations.status.in_({'pending', 'active', 'confirmed'}))).first()
    inactive_reservations = db.exec(select(func.count()).select_from(Reservations).where(Reservations.status.in_({'completed', 'cancelled'}))).first()
    all_reservations = db.exec(select(func.count()).select_from(Reservations)).first()
    
    return {'active': active_reservations, 'inactive': inactive_reservations, 'all': all_reservations}

@router.get("/reservations")
async def get_reservations(db:SessionDep, status: str | None = None, cursor: int | None = None, limit: int | None = None, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    if not limit:
        limit = 20
        
    match status:
        case 'active':
            db_statuses = {'pending', 'active', 'confirmed'}
        case 'inactive':
            db_statuses = {'completed', 'cancelled'}
        case _:
            db_statuses = {'pending', 'active', 'confirmed', 'completed', 'cancelled'}
            
    condition = [Reservations.status.in_(db_statuses)]
    if cursor:
        condition.append(Reservations.id >= cursor)
    stmt = select(Reservations, Cars).where(*condition).join(Cars).order_by(Reservations.id).limit(limit + 1).all()
    results = db.exec(stmt)
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
    
@router.patch("/reservations/approve/{id}")
def approve_reservations(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    reservation = db.exec(select(Reservations).where(Reservations.id == id)).first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

    setattr(reservation, 'status', 'confirmed')
        
    db.add(reservation)
    db.commit()
    
    return {'detail': 'Reservation successfully updated'}

@router.patch("/reservations/cancel/{id}")
def cancel_reservation(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    reservation = db.exec(select(Reservations).where(Reservations.id == id)).first()
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

    setattr(reservation, 'status', 'cancelled')
        
    db.add(reservation)
    db.commit()
    
    return {'detail': 'Reservation successfully updated'}

@router.get("/cars")
async def get_cars(db: SessionDep, stat: str | None = None, cursor: int | None = None, limit: int | None = None, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    if not limit:
        limit = 20
        
    conditions = []
    if cursor:
        conditions.append(Cars.id >= cursor)
    if stat == 'active':
        conditions.append(Cars.is_active == True)
    elif stat == 'inactive':
        conditions.append(Cars.is_active == False)
    
    if len(conditions) > 0:
        stmt = select(Cars).where(*conditions).order_by(Cars.id).limit(limit + 1)
    else:
        stmt = select(Cars).order_by(Cars.id).limit(limit + 1)
    
    db_cars = db.exec(stmt).all()
    if not db_cars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    cars = [car.model_dump() for car in db_cars]
        
    if len(cars) > limit:
        cursor = cars.pop()['id']
    else:
        cursor = None
    
    return {'items': cars, 'cursor': cursor}

@router.patch("/cars/set_inactive/{id}")
async def set_inactive(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    car = db.exec(select(Cars).where(Cars.id == id)).first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
    setattr(car, 'is_active', False)
    db.add(car)
    db.commit()
    
    return {'detail': f'Status set to inactive for car ID {car.id}'}

@router.patch("/cars/set_active/{id}")
async def set_active(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    car = db.exec(select(Cars).where(Cars.id == id)).first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
    setattr(car, 'is_active', True)
    db.add(car)
    db.commit()
    
    return {'detail': f'Status set to active for car ID {car.id}'}

@router.delete("/cars/delete/{id}")
async def delete_car(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    car = db.exec(select(Cars).where(Cars.id == id)).first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
    car_imgs = db.exec(select(CarImages).where(CarImages.car_id == car.id)).all()
    for img in car_imgs:
        db.delete(img)
        db.commit()
    
    db.delete(car)
    db.commit()
    
    return {'detail': f'Deleted car ID {car.id}'}