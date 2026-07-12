import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.user import User

# auto_error=False so we can return a uniform 401 for both missing and malformed
# credentials rather than letting FastAPI raise its own 403.
_bearer = HTTPBearer(auto_error=False)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = session.query(User).where(
        User.api_key_hash == hash_api_key(credentials.credentials)
    ).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
