from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from backend.main import app
from backend.db import engine
from backend.models import Users, Cars, Reservations
from backend.user import hash_password
from sqlmodel import Session, select
from uuid import uuid4
import pytest


client = TestClient(app)

@pytest.fixture(scope="function")
def info(): 
   with Session(engine) as db:
       hashed_pwd = hash_password('test_password')
       
       user = Users(
           first_name="Test First",
           last_name="Test Last",
           email="user@test.com",
           password_hash=hashed_pwd,
           is_admin=False,
       )

       admin = Users(
           first_name="Test First",
           last_name="Test Last",
           email="admin@test.com",
           password_hash=hashed_pwd,
           is_admin=True,
       )

       car = Cars(
           make="Test",
           model="Test",
           year=2000,
           seats=4,
           transmission="manual",
           daily_rate=50,
           description="Test"
       )

       db.add(user)
       db.add(admin)
       db.add(car)
       db.commit()
       db.refresh(car)
       db.refresh(user)
       db.refresh(admin)
       
       car_id = car.id

       reservation = Reservations(
           car_id=car.id,
           user_email=user.email,
           user_first_name=user.first_name,
           user_last_name=user.last_name,
           start_at=(datetime.now(timezone.utc)).date().isoformat(),
           end_at=(datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
           total_amount=50
       )

       db.add(reservation)
       db.commit()
       db.refresh(reservation)
       
       resp = client.post("/user/token", data={
           'username': user.email,
           'password': 'test_password'
           })
       user_access_token = resp.json()['access_token']
       
       resp = client.post("/user/token", data={
           'username': admin.email,
           'password': 'test_password'
           })
       admin_access_token = resp.json()['access_token']

       yield {
           'car': car, 
           'admin': admin, 
           'user': user, 
           'reservation': reservation,
           'user_access_token': user_access_token,
           'admin_access_token': admin_access_token
           }

       client.post("/user/logout", headers={'Authorization': f'Bearer {user_access_token}'})
       client.post("/user/logout", headers={'Authorization': f'Bearer {admin_access_token}'})
       db.delete(reservation)
       db.commit()
       db.delete(user)
       db.delete(admin)
       
       # our cars/delete endpoint test should delete the car, so it will not exist
       # in this scope
       car_exists = db.exec(select(Cars).where(Cars.id == car_id)).first()
       if car_exists:
           db.delete(car)
       db.commit()

class TestAdmin:
    def test_reservation_count(self, info):
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']

        resp_200 = client.get(
            "/admin/reservation_counts", 
            headers={'Authorization': f'Bearer {admin_access_token}'}
            )
        resp_401_non_admin = client.get(
            "/admin/reservation_counts", 
            headers={'Authorization': f'Bearer {user_access_token}'}
            )
        resp_401_invalid_token = client.get(
        "/admin/reservation_counts", 
        headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_401_non_admin.status_code == 401
        assert resp_401_invalid_token.status_code == 401
    
    def test_reservations(self, info):
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.get(
            "/admin/reservations",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.get(
            "/admin/reservations",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.get(
            "/admin/reservations",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_401_invalid_token.status_code == 401
        assert resp_401_non_admin.status_code == 401
        assert isinstance(resp_200.json()['items'], list)
        
    def test_reservations_approve(self, info):
        reservation = info['reservation']
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.patch(
            f"/admin/reservations/approve/{reservation.id}",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.patch(
            f"/admin/reservations/approve/{reservation.id}",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.patch(
            f"/admin/reservations/approve/{reservation.id}",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_200.json()['detail'] == 'Reservation successfully updated'
        assert resp_401_non_admin.status_code == 401
        assert resp_401_invalid_token.status_code == 401
        
    def test_reservation_cancel(self, info):
        reservation = info['reservation']
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.patch(
            f"/admin/reservations/cancel/{reservation.id}",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.patch(
            f"/admin/reservations/cancel/{reservation.id}",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.patch(
            f"/admin/reservations/cancel/{reservation.id}",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_200.json()['detail'] == 'Reservation successfully updated'
        assert resp_401_non_admin.status_code == 401
        assert resp_401_invalid_token.status_code == 401
        
    def test_cars(self, info):
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.get(
            f"/admin/cars",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.get(
            f"/admin/cars",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.get(
            f"/admin/cars",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )

        assert resp_200.status_code == 200
        assert isinstance(resp_200.json()['items'], list)
        assert resp_401_non_admin.status_code == 401
        assert resp_401_invalid_token.status_code == 401
    
    def test_cars_set_inactive(self, info):
        car = info['car']
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.patch(
            f"/admin/cars/set_inactive/{car.id}",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.patch(
            f"/admin/cars/set_inactive/{car.id}",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.patch(
            f"/admin/cars/set_inactive/{car.id}",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_200.json()['detail'] == f'Status set to inactive for car ID {car.id}'
        assert resp_401_invalid_token.status_code == 401
        assert resp_401_non_admin.status_code == 401
        
    def test_cars_set_inactive(self, info):
        car = info['car']
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        resp_200 = client.patch(
            f"/admin/cars/set_active/{car.id}",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.patch(
            f"/admin/cars/set_active/{car.id}",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.patch(
            f"/admin/cars/set_active/{car.id}",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )
        
        assert resp_200.status_code == 200
        assert resp_200.json()['detail'] == f'Status set to active for car ID {car.id}'
        assert resp_401_invalid_token.status_code == 401
        assert resp_401_non_admin.status_code == 401 
        
    def test_cars_delete(self, info):
        car = info['car']
        admin_access_token = info['admin_access_token']
        user_access_token = info['user_access_token']
        
        with Session(engine) as db:
            # Reservations table has a car.id foreign key, so we must delete them before deleting the 
            # associated car
            reservations = db.exec(select(Reservations).where(Reservations.car_id == car.id)).all()
            for r in reservations:
                db.delete(r)
            db.commit()
        
        resp_200 = client.delete(
            f"/admin/cars/delete/{car.id}",
            headers={'Authorization': f'Bearer {admin_access_token}'}
        )
        resp_401_non_admin = client.delete(
            f"/admin/cars/delete/{car.id}",
            headers={'Authorization': f'Bearer {user_access_token}'}
        )
        resp_401_invalid_token = client.delete(
            f"/admin/cars/delete/{car.id}",
            headers={'Authorization': f'Bearer {str(uuid4())}'}
        )

        assert resp_200.status_code == 200
        assert resp_200.json()['detail'] == f'Deleted car ID {car.id}'
        assert resp_401_invalid_token.status_code == 401
        assert resp_401_non_admin.status_code == 401 