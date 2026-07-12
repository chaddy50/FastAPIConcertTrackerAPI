"""Admin CLI for out-of-band user management.

Usage (run as a module from the repo root so `app` is importable):
    python -m scripts.manage rotate-key <username>   # regenerate a lost API key
    python -m scripts.manage list-users              # list usernames + created_at

Run on the server (with DATABASE_URL set). The core functions accept a Session
so they can be unit-tested against an in-memory database.
"""
import sys

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.auth import generate_api_key, hash_api_key

def rotate_key(username: str, session: Session) -> str:
    """Overwrite the user's api_key_hash with a fresh key, invalidating the old
    one while leaving all of the user's data (which references user.id) attached.
    Returns the new plaintext key."""
    user = session.query(User).where(User.username == username).first()
    if user is None:
        raise SystemExit(f"No user with username {username!r}")
    new_key = generate_api_key()
    user.api_key_hash = hash_api_key(new_key)
    session.commit()
    return new_key

def _cmd_rotate_key(username: str) -> None:
    with SessionLocal() as session:
        new_key = rotate_key(username, session)
    print(f"New key for {username}: {new_key}")
    print("Give this to the user — it will not be shown again.")


def list_users(session: Session) -> list[User]:
    return session.query(User).order_by(User.created_at).all()

def _cmd_list_users() -> None:
    with SessionLocal() as session:
        users = list_users(session)
    for user in users:
        print(f"{user.username}\t{user.created_at.isoformat()}")

def main(argv: list[str]) -> None:
    if len(argv) >= 2 and argv[1] == "rotate-key" and len(argv) == 3:
        _cmd_rotate_key(argv[2])
    elif len(argv) == 2 and argv[1] == "list-users":
        _cmd_list_users()
    else:
        raise SystemExit(
            "usage:\n"
            "  python -m scripts.manage rotate-key <username>\n"
            "  python -m scripts.manage list-users"
        )

if __name__ == "__main__":
    main(sys.argv)
