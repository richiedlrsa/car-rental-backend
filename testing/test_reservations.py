from fastapi.testclient import TestClient
from main import app
from db import engine
from models import Cars, Reservations
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
import random
import pytest

client = TestClient(app)

@pytest.fixture(scope="module")
def car():
    with Session(engine) as db:
        db_car = Cars(
             make='Test',
             model='Test',
             year=2000,
             seats=4,
             transmission='automatic',
             daily_rate=50,
             description='test'
        )
        db.add(db_car)
        db.commit()
        db.refresh(db_car)
        
        yield db_car
        
        db.delete(db_car)
        db.commit()
        
class TestReservations:
    def test_add_reservation(self, car):
        now = datetime.now(timezone.utc)
        reservation = {
            'car_id': car.id,
            'user_email': 'user@test.com',
            'user_first_name': 'Test First',
            'user_last_name': 'Test Last',
            'start_at': now.date().isoformat(),
            'end_at': (now + timedelta(days=random.randint(1, 5))).date().isoformat(),
            'total_amount': 50
        }
        reservation_conflict = {
            'car_id': car.id,
            'user_email': 'user@test.com',
            'user_first_name': 'Test First',
            'user_last_name': 'Test Last',
            'start_at': (now + timedelta(days=1)).date().isoformat(),
            'end_at': (now + timedelta(days=2)).date().isoformat(),
            'total_amount': 50
        }
        resp_200 = client.post('/reservations/add', json=reservation)
        resp_409 = client.post('/reservations/add', json=reservation_conflict) 
        assert resp_200.status_code == 200
        assert resp_409.status_code == 409
        assert resp_409.json()['detail'] == "The selected car is not available for these dates."
        
        with Session(engine) as db:
            reservations = db.exec(select(Reservations).where(Reservations.car_id == car.id)).all()
            for r in reservations:
                db.delete(r)
            db.commit()