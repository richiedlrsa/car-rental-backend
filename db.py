from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from typing import Annotated
from dotenv import find_dotenv, load_dotenv
import os

path = find_dotenv()
load_dotenv(path)
DB_URL = os.getenv('DB_URL')

engine = create_engine(DB_URL)

def get_session():
    with Session(engine) as session:
        yield session
        
SessionDep = Annotated[Session, Depends(get_session)]

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)