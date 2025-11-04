from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = 'refresh_token'
    REFRESH_COOKIE_PATH: str = '/'
    CSRF_COOKIE_NAME: str ='csrf_token'
    CSRF_HEADER_NAME: str = 'X-CSRF-Token'
    MEDIA_PATH: str = 'media'
    
settings = Settings()