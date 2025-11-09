from datetime import datetime, timezone, timedelta
from jose import jwt
from uuid import uuid4
from fastapi import Response
from config import settings
from dotenv import find_dotenv, load_dotenv
import os

path = find_dotenv()
load_dotenv(path)
SECRET_KEY = os.getenv('SECRET_KEY') 
ALGORITHM = os.getenv('ALGORITHM')

def create_access_token(email: str) -> str:
    '''
    creates an access token for the current user
    
    Input:
        email: the user's email
    Returns:
        an access token
    '''
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": expires
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(email: str) -> tuple:
    '''
    creates a refresh token for the current user
    
    Input:
        email: the user's email
    Returns:
        a tuple with the refresh token, its jti (unique id), the created at time, and the expire date of the token
    '''
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": email,
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp())
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, now, expires

def set_refresh_cookie(resp: Response, refresh_token: str, *, csrf_token: str) -> None:
    '''
    sets refresh cookies
    
    Input:
        resp: the response the cookies are being created for
        refresh_token: the refresh token to be included in the refresh token cookie
        csrf_token: the csrf token to be included in the csrf cookie
    Returns:
        None
    '''
    resp.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=False,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )
    resp.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=False,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    )

def clear_refresh_cookie(resp: Response) -> None:
    '''
    clears the refresh cookies
    
    Input:
        resp: the response the cookies are being cleared for
    Returns:
        None
    '''
    resp.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
    resp.delete_cookie(settings.CSRF_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)