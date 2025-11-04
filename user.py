from models import Users, UserBase
from db import SessionDep
from config import settings
from sqlmodel import select, Session
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import find_dotenv, load_dotenv
import os

path = find_dotenv()
load_dotenv(path)
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    '''
    verifies a plain text against a hashed password
    
    Input:
        plain_password: the plain text version of the password
        hashed_password: the hashed password
    Returns:
        a boolean indicating if the verification was successful or if it failed
    '''
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    '''
    runs password through hashing algorithm
    
    Input:
        password: a plain text password
    Returns:
        a hashed password
    '''
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, plain_password: str) -> tuple | None:
    '''
    checks if the email and password combination is correct
    
    Input:
        db: a database session
        email: the user's email
        password: the user's password
    Returns:
        a UserBase instance and the user id if the verification is successful, otherwise None
    '''
    stmt = select(Users).where(Users.email == email)
    user_in_db = db.exec(stmt).first()
    if not user_in_db:
        return None
    if not verify_password(plain_password, user_in_db.password_hash):
        return None
    user = UserBase(**user_in_db.model_dump(exclude={'id', 'password_hash'}))
    user_id = user_in_db.id
    return user, user_id

def get_current_user(db: SessionDep, token: str = Depends(oauth_2_scheme)) -> UserBase:
    '''
    validates the token and gets the user from the database
    
    Input: 
        db: a database engine
        token: the jwt token to validate
    Returns:
        a UserBase instance
    Raises:
        HTTPException (401): if the token is invalid, expired, or the user does not exist.
    '''
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not authenticate user",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credential_exception
    except JWTError:
        raise credential_exception
    
    stmt = select(Users).where(Users.email == email)
    curr_user = db.exec(stmt).first()
    if not curr_user:
        raise credential_exception
    user = UserBase(email=curr_user.email, first_name=curr_user.first_name, last_name=curr_user.last_name, is_admin=curr_user.is_admin)
    
    return user