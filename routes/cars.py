from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlmodel import select
from sqlalchemy import and_, not_, exists
from db import SessionDep
from models import Cars, CarBase, UserBase, CarImages, Reservations
from user import get_current_user
from config import settings
from imagekit import imagekit
from uuid import uuid4
from typing import List
from datetime import date
import os, shutil


router = APIRouter(prefix='/cars', tags=['cars'])

@router.post("/add_car")
async def add_car(db: SessionDep, car: CarBase = Depends(CarBase.as_form), images: List[UploadFile] = File(...), user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="You are not authorized to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
    
    db_car = Cars(**car)
    db.add(db_car)
    db.commit()
    db.refresh(db_car)
    
    saved_images: list[CarImages] = []
    folder = os.path.join(settings.MEDIA_PATH, f"cars/{db_car.id}")
    os.makedirs(folder, exist_ok=True)
    
    for i, img in enumerate(images):
        ext = os.path.splitext(img.filename or "")[1].lower() or ".bin"
        filename = f"{uuid4().hex}{ext}"
        dir_path = os.path.join(folder, filename)
        await img.seek(0)
        with open(dir_path, "wb") as f:
            shutil.copyfileobj(img.file, f)
            
        with open(dir_path, "rb") as f:
            upload = imagekit.upload_file(
                file=f,
                file_name=filename
            )
        image_url = upload.response_metadata.raw.get("url")
        if i == 0:
            image = CarImages(car_id=db_car.id, image_url=image_url, is_primary=True)
        else:
            image = CarImages(car_id=db_car.id, image_url=image_url)
        saved_images.append(image)
    
    db.add_all(saved_images)
    db.commit()
    
    return {"detail": "car added successfuly"}

@router.get("/available_cars")
async def get_available_cars(db: SessionDep, start: date, end: date):
    # if the start of a new reservation is <= the end of an existing AND the end of the 
    # new reservation >= the start of the existing reservation, ther's an overlap
    overlappin_res = and_(Reservations.start_at <= end, Reservations.end_at >= start, Reservations.status.in_(('pending', 'confirmed')))
    stmt = select(Cars).where(and_(not_(exists(select(Reservations.id).where(Reservations.car_id == Cars.id).where(overlappin_res)))), Cars.is_active)
    db_available_cars = db.exec(stmt).all()
    available_cars = []
    
    for car in db_available_cars:
        db_image = db.exec(select(CarImages).where(and_(CarImages.car_id == car.id), CarImages.is_primary == True)).first()
        car = car.model_dump()
        car['image_url'] = db_image.image_url if db_image else None
        available_cars.append(car)
    
    return available_cars

@router.get("/{id}")
async def get_car(db: SessionDep, id: int):
    db_car = db.exec(select(Cars).where(Cars.id == id)).first()
    if not db_car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find car")
    
    car = db_car.model_dump(exclude={'is_active'})
    db_images = db.exec(select(CarImages).where(CarImages.car_id == db_car.id)).all()
    images = [image.image_url for image in db_images]
    car['images'] = images
    
    return car