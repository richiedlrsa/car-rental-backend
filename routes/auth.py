from fastapi import APIRouter, Response, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from jose import JWTError, jwt
from uuid import uuid4
from config import settings
from db import SessionDep
from user import authenticate_user, get_current_user, hash_password
from jwt import create_access_token, create_refresh_token, set_refresh_cookie, clear_refresh_cookie
from models import RefreshTokens, UserToCreate, Users, UserBase
from dotenv import load_dotenv, find_dotenv
import os

path = find_dotenv()
load_dotenv(path)
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
router = APIRouter(prefix='/user', tags=['user'])

@router.post("/token")
async def get_access_token(db: SessionDep, response: Response, form_data: OAuth2PasswordRequestForm=Depends()):
    try:
        user, user_id = authenticate_user(db, form_data.username, form_data.password)
    except TypeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
            )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
            )
        
    access_token = create_access_token(user.email)
    refresh_token, jti, issued_at, expire_date = create_refresh_token(user.email)
    stmt = select(RefreshTokens).where(RefreshTokens.user_id == user_id)
    old_tokens = db.exec(stmt).all()
    for old_token in old_tokens:
        db.delete(old_token)
    db_refresh_token = RefreshTokens(jti=jti, user_id=user_id, issued_at=issued_at, expires_at=expire_date)
    db.add(db_refresh_token)
    db.commit()
    
    csrf_token = str(uuid4())
    set_refresh_cookie(resp=response, refresh_token=refresh_token, csrf_token=csrf_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")
async def create_new_user(db: SessionDep, user_info: UserToCreate, response: Response):
    stmt = select(Users).where(Users.email == user_info.email)
    user_exists = db.exec(stmt).first()
    if user_exists:
        raise HTTPException(status_code=409, detail="This email already exists")
    
    hashed_password = hash_password(user_info.password)
    new_user = Users(email=user_info.email, first_name=user_info.first_name, last_name=user_info.last_name, password_hash=hashed_password, is_admin=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    refresh_token, jti, issued_at, expire_date = create_refresh_token(new_user.email)
    db_refresh_token = RefreshTokens(jti=jti, user_id=new_user.id, issued_at=issued_at, expires_at=expire_date)
    db.add(db_refresh_token)
    db.commit()
    
    csrf_token = str(uuid4())
    set_refresh_cookie(resp=response, refresh_token=refresh_token, csrf_token=csrf_token)
    
    return {'detail': 'account created successfully'}

@router.get("/me", response_model=UserBase)
async def read_users_me(current_user: UserBase=Depends(get_current_user)):
    return UserBase(email=current_user.email, first_name=current_user.first_name, last_name=current_user.last_name, is_admin=current_user.is_admin)

@router.get("/refresh")
async def refresh_access_token(request: Request, response: Response):
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=ALGORITHM)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")
    
    jti = payload.get("jti")
    email = payload.get("sub")
    if not jti or not email:
        raise HTTPException(status_code=401, detail="Unknown refresh token")
    
    access_token = create_access_token(email)
    new_refresh_token = create_refresh_token(email)[0]
    
    csrf_token = str(uuid4())
    set_refresh_cookie(resp=response, refresh_token=new_refresh_token, csrf_token=csrf_token)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(db: SessionDep, response: Response, user: UserBase = Depends(get_current_user)):
    stmt = select(Users).where(Users.email == user.email)
    db_user = db.exec(stmt).first()
    tokens = db.exec(select(RefreshTokens).where(RefreshTokens.user_id == db_user.id)).all()
    for t in tokens:
        db.delete(t)
    
    db.commit()
    
    clear_refresh_cookie(response)
    
    return {"detail": "Logged out"}