from db import engine
from sqlmodel import Session, select
from main import app
from models import Users, RefreshTokens 
from user import hash_password
from fastapi.testclient import TestClient
from sqlmodel import select
from uuid import uuid4
import pytest

client = TestClient(app)

@pytest.fixture(scope="function")
def user_and_tokens():
    hashed_pwd = hash_password('test_password')
    with Session(engine) as db:
        user = Users(
            first_name="First Test",
            last_name="Last Test",
            email="user@test.com",
            password_hash=hashed_pwd,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        resp = client.post(
            '/user/token', 
            data={'username': user.email, 'password': 'test_password'}
            )
        access_token = resp.json()['access_token']
        csrf_token = resp.cookies.get('csrf_token')

        yield {'user': user, 'access_token': access_token, 'csrf_token': csrf_token}
        # prevent lingering tokens by deleted all tokens and clearing cookies
        client.post('/user/logout', headers={'Authorization': f'Bearer {access_token}'})
        user_to_delete = db.exec(select(Users).where(Users.id == user.id)).first()
        db.delete(user_to_delete)
        db.commit()

class TestAuth:
    def test_register(self):
       user_to_create = {
           'email': 'user@test.com',
           'first_name': 'Test First',
           'last_name': 'Test Last',
           'password': 'test_password'
       }
       resp_200 = client.post('/user/register', json=user_to_create)
       resp_409 = client.post('/user/register', json=user_to_create) 
       assert resp_200.status_code == 200
       assert resp_200.json()['detail'] == 'account created successfully'
       assert resp_409.status_code == 409

       # the register route adds the user to the db, so we must delete it
       with Session(engine) as db:
           db_user = db.exec(select(Users).where(Users.email == user_to_create['email'])).first()
           
           if db_user:
            db.delete(db_user)
            db.commit()
       
    def test_login(self, user_and_tokens):
        user = user_and_tokens['user']
        resp_200 = client.post(
            '/user/token', 
            data={'username': user.email, 'password': 'test_password'}) 
        resp_401_incorrect_password = client.post('/user/token', data={
            'username': user.email,
            'password': 'incorrect_password'
        })
        resp_401_incorrect_email = client.post('/user/token', data={
                'username': 'email@incorrect.com',
                'password': 'test_password'
            })
        access_token = resp_200.json()['access_token']
        csrf_token = resp_200.cookies.get('csrf_token')
        assert resp_200.status_code == 200
        assert isinstance(access_token, str)
        assert resp_200.json()['token_type'] == 'bearer'
        assert resp_401_incorrect_password.status_code == 401
        assert resp_401_incorrect_password.json()['detail'] == 'Incorrect username or password'
        assert resp_401_incorrect_email.status_code == 401
        assert resp_401_incorrect_email.json()['detail'] == 'Incorrect username or password'
        assert csrf_token
    
    def test_me(self, user_and_tokens):
        access_token = user_and_tokens['access_token']
        user = user_and_tokens['user']
        resp_user_200 = client.get('/user/me', headers={'Authorization': f"Bearer {access_token}"})
        resp_user_401 = client.get('/user/me', headers={'Authorization': f"Bearer {str(uuid4())}"})
        returned_user = resp_user_200.json()
        assert resp_user_200.status_code == 200
        assert returned_user['email'] == user.email
        assert returned_user['first_name'] == user.first_name
        assert returned_user['last_name'] == user.last_name
        assert returned_user['is_admin'] == False
        assert resp_user_401.status_code == 401
        
    def test_refresh(self, user_and_tokens):
        csrf_token = user_and_tokens['csrf_token']
        resp_csrf_200 = client.get('/user/refresh', headers={'X-CSRF-Token': csrf_token})
        resp_csrf_403_wrong_csrf = client.get('/user/refresh', headers={'X-CSRF-Token': str(uuid4())})
        resp_csrf_403_no_csrf = client.get('/user/refresh')
        new_access_token = resp_csrf_200.json()['access_token']
        assert resp_csrf_200.status_code == 200
        assert resp_csrf_200.json()['token_type'] == 'bearer'
        assert isinstance(new_access_token, str)
        assert resp_csrf_403_wrong_csrf.status_code == 403
        assert resp_csrf_403_no_csrf.status_code == 403
    
    def test_logout(self, user_and_tokens):
        access_token = user_and_tokens['access_token']
        user = user_and_tokens['user']
        resp_logout_200 = client.post('user/logout', headers={'Authorization': f"Bearer {access_token}"})
        assert resp_logout_200.status_code == 200
        assert resp_logout_200.json()['detail'] == 'Logged out'
        with Session(engine) as db:
            refresh_tokens = db.exec(select(RefreshTokens).where(RefreshTokens.user_id == user.id)).all()
        
        assert not refresh_tokens