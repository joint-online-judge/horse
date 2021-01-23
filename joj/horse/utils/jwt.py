from datetime import datetime, timedelta
import jose.jwt
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from joj.horse.config import settings
from joj.horse.models.user import get_by_uname, User

class JWTToken(BaseModel):
    aud: str
    iss: str
    sub: str
    exp: str
    iat: str
    name: str
    code: str
    type: str

async def get_current_user(jwt_token: str = None):
    try:
        payload = jose.jwt.decode(jwt_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    except Exception:
        return None


async def generate_jwt(user: User):
    to_encode = {
        'sub': user.uname_lower,
        'scope': user.scope,
        'exp': datetime.utcnow() + timedelta(seconds=settings.jwt_expire_seconds)
    }
    encoded_jwt = jose.jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt
