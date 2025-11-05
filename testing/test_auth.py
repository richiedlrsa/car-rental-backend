from backend.db import engine
from sqlmodel import Session, select
from backend.main import app
from backend.models import Users, RefreshTokens 
from fastapi.testclient import TestClient
from sqlmodel import select
from string import ascii_lowercase
from uuid import uuid4
import random as r
import pytest

client = TestClient(app)


@pytest.fixture(scope="module")
def test_user():
    domain = '@test.com'
    username_length = r.randint(5, 10)
    username = ''.join([r.choice(ascii_lowercase) for _ in range(username_length + 1)])
    email = username + domain
    
    yield {'email': email, 'password': 'test_password'}
    
    with Session(engine) as db:
        db_user = db.exec(select(Users).where(Users.email == email)).first()
        if db_user:
            refresh_token = db.exec(select(RefreshTokens).where(RefreshTokens.user_id == db_user.id)).all()
            for t in refresh_token:
                db.delete(t)
            db.delete(db_user)
            db.commit()

class TestAuth:
    def test_register(self, test_user):
       user_to_create = {'email': test_user['email'],
                         'first_name': 'Test First',
                         'last_name': 'Test Last',
                         'password': test_user['password']}
       resp_200 = client.post('/user/register', json=user_to_create)
       resp_409 = client.post('/user/register', json=user_to_create) 
       assert resp_200.status_code == 200
       assert resp_200.json()['detail'] == 'account created successfully'
       assert resp_409.status_code == 409
       
    def test_login_and_logout(self, test_user):
        resp_200 = client.post('/user/token', data={'username': test_user['email'], 'password': test_user['password']})
        resp_401_incorrect_password = client.post('/user/token', data={
            'username': test_user['email'],
            'password': 'incorrect_password'
        })
        resp_401_incorrect_email = client.post('/user/token', data={
                'username': 'email@incorrect.com',
                'password': test_user['password']
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
        
        resp_user_200 = client.get('/user/me', headers={'Authorization': f"Bearer {access_token}"})
        resp_user_401 = client.get('/user/me', headers={'Authorization': f"Bearer {str(uuid4())}"})
        user = resp_user_200.json()
        assert resp_user_200.status_code == 200
        assert user['email'] == test_user['email']
        assert user['first_name'] == 'Test First'
        assert user['last_name'] == 'Test Last'
        assert user['is_admin'] == False
        assert resp_user_401.status_code == 401
        
        resp_csrf_200 = client.get('/user/refresh', headers={'X-CSRF-Token': csrf_token})
        resp_csrf_403_wrong_csrf = client.get('/user/refresh', headers={'X-CSRF-Token': str(uuid4())})
        resp_csrf_403_no_csrf = client.get('/user/refresh')
        assert resp_csrf_200.status_code == 200
        assert resp_csrf_200.json()['token_type'] == 'bearer'
        assert isinstance(resp_csrf_200.json()['access_token'], str)
        assert resp_csrf_403_wrong_csrf.status_code == 403
        assert resp_csrf_403_no_csrf.status_code == 403
    
        resp_logout_200 = client.post('user/logout', headers={'Authorization': f"Bearer {access_token}"})
        assert resp_logout_200.status_code == 200
        assert resp_logout_200.json()['detail'] == 'Logged out'
        with Session(engine) as db:
            user = db.exec(select(Users).where(Users.email == test_user['email'])).first()
            refresh_tokens = db.exec(select(RefreshTokens).where(RefreshTokens.user_id == user.id)).all()
        
        assert not refresh_tokens