from unittest.mock import patch

from app.cli import ensure_admin_user_exists
from app.models.user import User
from app.security import verify_password


def test_seeds_admin_user_when_none_exist(db):
    assert db.query(User).count() == 0

    with patch("app.cli.settings.admin_username", "seeduser"), patch(
        "app.cli.settings.admin_password", "seedpass123"
    ):
        ensure_admin_user_exists()

    user = db.query(User).filter(User.username == "seeduser").first()
    assert user is not None
    assert verify_password("seedpass123", user.password_hash)


def test_does_not_touch_existing_users(db):
    db.add(User(username="existing", password_hash="already-hashed"))
    db.commit()

    with patch("app.cli.settings.admin_username", "admin"), patch("app.cli.settings.admin_password", "admin"):
        ensure_admin_user_exists()

    # No new user created, and the existing one's hash is untouched.
    assert db.query(User).count() == 1
    user = db.query(User).filter(User.username == "existing").first()
    assert user.password_hash == "already-hashed"
