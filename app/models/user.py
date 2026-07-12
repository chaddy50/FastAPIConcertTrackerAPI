from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base
from app.models.base_schema import ReadSchema, Schema


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RegisterRequest(Schema):
    username: str


class RegisterResponse(Schema):
    id: str
    username: str
    api_key: str  # plaintext key, returned exactly once at registration


class UserRead(ReadSchema):
    id: str
    username: str
    created_at: datetime  # never includes the key or its hash
