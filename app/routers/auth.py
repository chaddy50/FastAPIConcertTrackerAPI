from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.user import RegisterRequest, RegisterResponse, User, UserRead
from app.auth import CurrentUserDep, generate_api_key, hash_api_key

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(data: RegisterRequest, session: SessionDep):
    username = data.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="Username is required")
    if session.query(User).where(User.username == username).first():
        raise HTTPException(status_code=409, detail=f"Username {username} already taken")
    key = generate_api_key()
    user = User(username=username, api_key_hash=hash_api_key(key))
    session.add(user)
    session.commit()
    session.refresh(user)
    return RegisterResponse(id=user.id, username=user.username, api_key=key)


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUserDep):
    return current_user
