from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr, BaseModel, ConfigDict
from datetime import datetime, date, timezone
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, Numeric
from fastapi import Form
from typing import List

class ReservationStatus(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    cancelled = 'cancelled'
    completed = 'completed'
    active = 'active'

class Transmission(str, Enum):
    automatic = 'automatic'
    manual = 'manual'

class Cars(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    make: str = Field(nullable=False)
    model: str = Field(nullable=False)
    year: int = Field(nullable=False)
    seats: int = Field()
    transmission: Transmission = Field()
    daily_rate: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    description: str = Field(nullable=False)
    images: List[CarImages] = Relationship(back_populates='car')
    is_active: bool = Field(default=True, nullable=False)
    model_config = ConfigDict(from_attributes=True)
    
class Reservations(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    car_id: int = Field(nullable=False, foreign_key='cars.id')
    user_email: EmailStr = Field(nullable=False)
    user_first_name: str = Field(nullable=False)
    user_last_name: str = Field(nullable=False)
    start_at: date = Field(nullable=False)
    end_at: date = Field(nullable=False)
    status: ReservationStatus = Field(default=ReservationStatus.pending)
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(from_attributes=True)

class Users(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    email: EmailStr = Field(nullable=False, unique=True)
    password_hash: str = Field(nullable=False)
    is_admin: bool = Field(default=False)
    model_config = ConfigDict(from_attributes=True)
    
class CarImages(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    car_id: int = Field(nullable=False, foreign_key='cars.id')
    image_url: str = Field(nullable=False)
    is_primary: bool = Field(default=False)
    car: Cars = Relationship(back_populates='images')
    model_config = ConfigDict(from_attributes=True)
    
class RefreshTokens(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    jti: str = Field(nullable=False, unique=True)
    user_id: int = Field(nullable=False, foreign_key='users.id')
    issued_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)
    
class CarBase(BaseModel):
    make: str
    model: str
    year: int
    seats: int
    transmission: str
    daily_rate: float
    description: str
    
    @classmethod
    def as_form(
        cls,
        make: str = Form(...),
        model: str = Form(...),
        year: int = Form(...),
        seats: int = Form(...),
        transmission: str = Form(...),
        daily_rate: float = Form(...),
        description: str = Form(...)
    ):
        return cls(
            make=make, model=model, year=year, seats=seats,
            transmission=transmission, daily_rate=daily_rate,
            description=description
        )
    
class Token(BaseModel):
    access_token: str
    token_type: str
    
class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    is_admin: bool
    
class UserToCreate(BaseModel):
    email: str
    first_name: str
    last_name: str
    password: str
    
class ReservationBase(BaseModel):
    car_id: int = Field(nullable=False, foreign_key='car.id')
    user: EmailStr = Field(nullable=False)
    start_at: date = Field(nullable=False)
    end_at: date = Field(nullable=False)
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    model_config = ConfigDict(from_attributes=True)