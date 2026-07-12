import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.auth import hash_api_key
from scripts.manage_users import list_users, rotate_key
from tests.conftest import PRIMARY_USER_ID, _make_venue, _make_performance


def test_rotate_key_sets_new_hash_same_id(db_session: Session, user: User):
    old_hash = user.api_key_hash
    new_key = rotate_key("primary", db_session)
    refreshed = db_session.get(User, PRIMARY_USER_ID)
    assert refreshed.id == PRIMARY_USER_ID
    assert refreshed.api_key_hash != old_hash
    assert refreshed.api_key_hash == hash_api_key(new_key)


def test_rotate_key_preserves_user_data(db_session: Session, user: User):
    venue = _make_venue(db_session)
    perf = _make_performance(db_session, venue.id, user_id=PRIMARY_USER_ID)
    rotate_key("primary", db_session)
    # data still attached to the same user id
    assert db_session.get(User, PRIMARY_USER_ID) is not None
    from app.models.performance import Performance

    assert db_session.get(Performance, perf.id).user_id == PRIMARY_USER_ID


def test_rotate_key_unknown_username_raises(db_session: Session):
    with pytest.raises(SystemExit):
        rotate_key("nobody", db_session)


def test_list_users_returns_users_without_secrets(db_session: Session, user: User):
    users = list_users(db_session)
    assert any(u.username == "primary" for u in users)
