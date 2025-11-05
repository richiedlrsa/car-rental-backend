from backend.auth_tokens import create_access_token, create_refresh_token
from backend.config import settings
from backend.user import verify_password, hash_password
from jose import jwt, JWTError
from dotenv import find_dotenv, load_dotenv
from datetime import timedelta
import os
import pytest

path = find_dotenv()
load_dotenv(path)
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
WRONG_SECRET_KEY = 'leHmYZFIU6S3Jb72qeM3vuwwB6Kx4sLg'
WRONG_TOKEN = 'AtXpVZ9Kew75dgCOrZ3PmqF6mD7jc0zg'

class TestJwt:
    def test_sign_access_token(self):
        access_token = create_access_token('user@example.com')
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload['sub'] == 'user@example.com'
        assert payload['type'] == 'access'
        assert isinstance(access_token, str)
        with pytest.raises(JWTError):
            jwt.decode(WRONG_TOKEN, SECRET_KEY, algorithms=[ALGORITHM])
        with pytest.raises(JWTError):
            jwt.decode(access_token, WRONG_SECRET_KEY, algorithms=[ALGORITHM])
            
    def test_sign_refresh_token(self):
        token, jti, iat, expires = create_refresh_token('user@example.com')
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload['sub'] == 'user@example.com'
        assert payload['type'] == 'refresh'
        assert payload['jti'] == jti
        assert payload['exp'] == int(expires.timestamp())
        assert expires - timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS) == iat
        assert isinstance(token, str)
        assert isinstance(jti, str)
        with pytest.raises(JWTError):
            jwt.decode(token, WRONG_SECRET_KEY, algorithms=[ALGORITHM])
        with pytest.raises(JWTError):
            jwt.decode(WRONG_TOKEN, SECRET_KEY, algorithms=[ALGORITHM])