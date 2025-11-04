# from fastapi import APIRouter, HTTPException, status, Depends, Response, Request, UploadFile, File
# from fastapi.security import OAuth2PasswordRequestForm
# from fastapi.staticfiles import StaticFiles
# from sqlmodel import select
# from sqlalchemy import and_, not_, exists, func
# from sqlalchemy.exc import IntegrityError
# from uuid import uuid4
# from models import Token, Users, UserBase, UserToCreate, RefreshToken, CarBase, Car, CarImage, Reservation, ReservationBase, ReservationUpdate
# from user import authenticate_user, hash_password, get_current_user
# from jwt import create_access_token, create_refresh_token, set_refresh_cookie, clear_refresh_cookie
# from db import SessionDep
# from config import settings
# from typing import List
# import os, shutil
# from datetime import date
# from imagekit import imagekit
# from jose import JWTError, jwt

# router = APIRouter()
# MEDIA_ROOT = 'media'
# BASE_URL = '/media'
# router.mount(BASE_URL, StaticFiles(directory=MEDIA_ROOT))

# @router.post("/token", response_model=Token)
# async def get_access_token(db: SessionDep, response: Response, form_data: OAuth2PasswordRequestForm=Depends()):
#     try:
#         user, user_id = authenticate_user(db, form_data.username, form_data.password)
#     except TypeError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     access_token = create_access_token(user.email)
#     refresh_token, jti, issued_at, expire_date = create_refresh_token(user.email)
#     stmt = select(RefreshToken).where(RefreshToken.user_id == user_id)
#     old_tokens = db.exec(stmt).all()
#     for old_token in old_tokens:
#         db.delete(old_token)
#     db_refresh_token = RefreshToken(jti=jti, user_id=user_id, issued_at=issued_at, expires_at=expire_date)
#     db.add(db_refresh_token)
#     db.commit()
    
#     csrf_token = str(uuid4())
#     set_refresh_cookie(resp=response, refresh_token=refresh_token, csrf_token=csrf_token)
    
#     return {"access_token": access_token, "token_type": "bearer"}

# @router.post("/register", status_code=status.HTTP_201_CREATED)
# async def create_new_user(db: SessionDep, user_info: UserToCreate, response: Response):
#     stmt = select(Users).where(Users.email == user_info.email)
#     user_exists = db.exec(stmt).first()
#     if user_exists:
#         raise HTTPException(status_code=409, detail="This email already exists")
    
#     hashed_password = hash_password(user_info.password)
#     new_user = Users(email=user_info.email, first_name=user_info.first_name, last_name=user_info.last_name, password_hash=hashed_password, is_admin=True)
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
    
#     refresh_token, jti, issued_at, expire_date = create_refresh_token(new_user.email)
#     db_refresh_token = RefreshToken(jti=jti, user_id=new_user.id, issued_at=issued_at, expires_at=expire_date)
#     db.add(db_refresh_token)
#     db.commit()
    
#     csrf_token = str(uuid4())
#     set_refresh_cookie(resp=response, refresh_token=refresh_token, csrf_token=csrf_token)
    
#     user = UserBase(email=user_info.email, first_name=user_info.first_name, last_name=user_info.last_name, is_admin=False)
    
#     return user

# @router.get("/me", response_model=UserBase)
# async def read_users_me(current_user: UserBase=Depends(get_current_user)):
#     return UserBase(email=current_user.email, first_name=current_user.first_name, last_name=current_user.last_name, is_admin=current_user.is_admin)

# @router.get("/refresh", response_model=Token)
# async def refresh_access_token(db: SessionDep, request: Request, response: Response):
#     csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
#     csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
#     if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
#         raise HTTPException(status_code=403, detail="CSRF validation failed")

#     refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
#     if not refresh_token:
#         raise HTTPException(status_code=401, detail="Missing refresh token")
    
#     try:
#         payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid refresh token")
    
#     if payload.get("type") != "refresh":
#         raise HTTPException(status_code=401, detail="Wrong token type")
    
#     jti = payload.get("jti")
#     email = payload.get("sub")
#     if not jti or not email:
#         raise HTTPException(status_code=401, detail="Unknown refresh token")
    
#     access_token = create_access_token(email)
#     new_refresh_token = create_refresh_token(email)[0]
    
#     csrf_token = str(uuid4())
#     set_refresh_cookie(resp=response, refresh_token=new_refresh_token, csrf_token=csrf_token)
    
#     return {"access_token": access_token, "token_type": "bearer"}

# @router.post("/logout")
# async def logout(response: Response):
#     clear_refresh_cookie(response)
#     return {"detail": "Logged out"}

# @router.post("/add_car")
# async def add_car(db: SessionDep, car: CarBase = Depends(CarBase.as_form), images: List[UploadFile] = File(...), user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
    
#     db_car = Car(
#         make=car.make, model=car.model, year=car.year, seats=car.seats,
#         transmission=car.transmission, daily_rate=car.daily_rate,
#         description=car.description
#     )
#     db.add(db_car)
#     db.commit()
#     db.refresh(db_car)
    
#     saved_images: list[CarImage] = []
#     folder = os.path.join("media", f"cars/{db_car.id}")
#     os.makedirs(folder, exist_ok=True)
    
#     for i, img in enumerate(images):
#         ext = os.path.splitext(img.filename or "")[1].lower() or ".bin"
#         filename = f"{uuid4().hex}{ext}"
#         dir_path = os.path.join(folder, filename)
#         await img.seek(0)
#         with open(dir_path, "wb") as f:
#             shutil.copyfileobj(img.file, f)
            
#         with open(dir_path, "rb") as f:
#             upload = imagekit.upload_file(
#                 file=f,
#                 file_name=filename
#             )
#         image_url = upload.response_metadata.raw.get("url")
#         if i == 0:
#             image = CarImage(car_id=db_car.id, image_url=image_url, is_primary=True)
#         else:
#             image = CarImage(car_id=db_car.id, image_url=image_url)
#         saved_images.append(image)
    
#     db.add_all(saved_images)
#     db.commit()
    
#     return {"detail": "cars added successfuly"}

# @router.get("/available_cars")
# async def get_available_cars(db: SessionDep, start: date, end: date):
#     # if the start of a new reservation is <= the end of an existing AND the end of the 
#     # new reservation >= the start of the existing reservation, ther's an overlap
#     overlappin_res = and_(Reservation.start_at <= end, Reservation.end_at >= start, Reservation.status.in_(('pending', 'confirmed')))
#     stmt = select(Car).where(and_(not_(exists(select(Reservation.id).where(Reservation.car_id == Car.id).where(overlappin_res)))), Car.is_active)
#     db_available_cars = db.exec(stmt).all()
#     available_cars = []
    
#     for car in db_available_cars:
#         db_image = db.exec(select(CarImage).where(and_(CarImage.car_id == car.id), CarImage.is_primary == True)).first()
#         car = car.model_dump()
#         car['image_url'] = db_image.image_url if db_image else None
#         available_cars.append(car)
    
#     return available_cars


# @router.get("/admin/reservation_counts")
# async def get_reservation_counts(db: SessionDep, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
    
#     active_reservations = db.exec(select(func.count()).select_from(Reservation).where(Reservation.status.in_({'pending', 'active', 'confirmed'}))).first()
#     inactive_reservations = db.exec(select(func.count()).select_from(Reservation).where(Reservation.status.in_({'completed', 'cancelled'}))).first()
#     all_reservations = db.exec(select(func.count()).select_from(Reservation)).first()
    
#     return {'active': active_reservations, 'inactive': inactive_reservations, 'all': all_reservations}


# @router.get("/car/{id}")
# async def get_car(db: SessionDep, id: int):
#     db_car = db.exec(select(Car).where(Car.id == id)).first()
#     if not db_car:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find car")
    
#     car = db_car.model_dump(exclude={'is_active'})
#     db_images = db.exec(select(CarImage).where(CarImage.car_id == db_car.id)).all()
#     images = [image.image_url for image in db_images]
#     car['images'] = images
    
#     return car

# @router.post("/reservations/add")
# async def add_reservation(db: SessionDep, reservation: ReservationBase):
#     check_overlap = db.exec(select(Reservation).where(Reservation.car_id == reservation.car_id, Reservation.status.in_({'confirmed', 'pending', 'active'}))).all()
#     for r in check_overlap:
#         if r.start_at <= reservation.end_at and r.end_at >= reservation.start_at:
#             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected car is not available for these dates")
#     db_reservation = Reservation(**reservation.model_dump())
#     try:
#         db.add(db_reservation)
#         db.commit()
#     except IntegrityError:
#         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected car is not available for these dates")

#     return {"success": "reservation successfully added"}

# @router.get("/admin/reservations")
# async def get_reservations(db:SessionDep, status: str | None = None, cursor: int | None = None, limit: int | None = None, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     if not limit:
#         limit = 20
        
#     match status:
#         case 'active':
#             db_statuses = {'pending', 'active', 'confirmed'}
#         case 'inactive':
#             db_statuses = {'completed', 'cancelled'}
#         case _:
#             db_statuses = {'pending', 'active', 'confirmed', 'completed', 'cancelled'}
            
#     condition = [Reservation.status.in_(db_statuses)]
#     if cursor:
#         condition.append(Reservation.id > cursor)
#     reservations = db.exec(select(Reservation).where(*condition).order_by(Reservation.id).limit(limit)).all()
#     if not reservations:
#         return {'response': f'No {status if status != 'all' else 'found'} reservations'}
#     reservations_resp = []
#     for res in reservations:
#         car = db.exec(select(Car).where(Car.id == res.car_id)).first()
#         car_info = {'id': car.id, 'make': car.make, 'model': car.model, 'year': car.year}
#         reservation = res.model_dump(exclude={'car_id', 'created_at'})
#         reservation['car'] = car_info
#         reservations_resp.append(reservation)
    
#     if len(reservations_resp) >= limit:
#         cursor = reservations_resp[-1]['id']
#     else:
#         cursor = None
        
#     return {'items': reservations_resp, 'next_cursor': cursor}
    
# @router.patch("/admin/reservations/approve/{id}")
# def approve_reservations(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     reservation = db.exec(select(Reservation).where(Reservation.id == id)).first()
#     if not reservation:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

#     setattr(reservation, 'status', 'confirmed')
        
#     db.add(reservation)
#     db.commit()
    
#     return {'status': 'Reservation successfully updated'}

# @router.patch("/admin/reservations/cancel/{id}")
# def cancel_reservation(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     reservation = db.exec(select(Reservation).where(Reservation.id == id)).first()
#     if not reservation:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reservation not found')

#     setattr(reservation, 'status', 'cancelled')
        
#     db.add(reservation)
#     db.commit()
    
#     return {'status': 'Reservation successfully updated'}

# @router.get("/admin/cars")
# async def get_cars(db: SessionDep, stat: str | None = None, cursor: int | None = None, limit: int | None = None, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     if not limit:
#         limit = 20
        
#     conditions = []
#     if cursor:
#         conditions.append(Car.id > cursor)
#     if stat == 'active':
#         conditions.append(Car.is_active == True)
#     elif stat == 'inactive':
#         conditions.append(Car.is_active == False)
    
#     if len(conditions) > 0:
#         stmt = select(Car).where(*conditions).order_by(Car.id).limit(limit)
#     else:
#         stmt = select(Car).order_by(Car.id).limit(limit)
    
#     db_cars = db.exec(stmt).all()
#     if not db_cars:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
#     cars = []
#     for car in db_cars:
#         curr_car = car.model_dump(exclude={'seats', 'transmission', 'daily_rate', 'description', 'is_active'})
#         if car.is_active:
#             curr_car['status'] = 'active'
#         else:
#             curr_car['status'] = 'inactive'
#         cars.append(curr_car)
        
#     if len(cars) >= limit:
#         cursor = cars[-1]['id']
#     else:
#         cursor = None
    
#     return {'items': cars, 'cursor': cursor}

# @router.patch("/admin/cars/set_inactive/{id}")
# async def set_inactive(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     car = db.exec(select(Car).where(Car.id == id)).first()
#     if not car:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
#     setattr(car, 'is_active', False)
#     db.add(car)
#     db.commit()
    
#     return {'detail': f'Status set to inactive for car ID {car.id}'}

# @router.patch("/admin/cars/set_active/{id}")
# async def set_active(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     car = db.exec(select(Car).where(Car.id == id)).first()
#     if not car:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
#     setattr(car, 'is_active', True)
#     db.add(car)
#     db.commit()
    
#     return {'detail': f'Status set to active for car ID {car.id}'}

# @router.delete("/admin/cars/delete/{id}")
# async def delete_car(db: SessionDep, id: int, user: UserBase = Depends(get_current_user)):
#     if not user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="You are not authorized to perform this action",
#             headers={"WWW-Authenticate": "Bearer"}
#             )
        
#     car = db.exec(select(Car).where(Car.id == id)).first()
#     if not car:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No cars found')
    
#     car_imgs = db.exec(select(CarImage).where(CarImage.car_id == car.id)).all()
#     for img in car_imgs:
#         db.delete(img)
#         db.commit()
    
#     db.delete(car)
#     db.commit()
    
#     return {'detail': f'Deleted car ID {car.id}'}