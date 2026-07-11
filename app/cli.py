import argparse
import getpass
import logging
import sys

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.security import hash_password

logger = logging.getLogger(__name__)


def ensure_admin_user_exists() -> None:
    """If no users exist yet, seed one from ADMIN_USERNAME/ADMIN_PASSWORD in
    .env -- makes a fresh deployment (Docker especially, where running an
    interactive `docker compose exec` command is an easy step to miss) usable
    immediately, matching what .env.example's own comment already implies.
    Never touches an existing user, so this is a no-op on every restart once
    real credentials are in place."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
        db.commit()
        logger.warning(
            "No admin user existed yet; created '%s' from ADMIN_USERNAME/ADMIN_PASSWORD in .env. "
            "Change this password after logging in if it's still the default.",
            settings.admin_username,
        )
    finally:
        db.close()


def create_user(username: str, password: str | None) -> None:
    if password is None:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match", file=sys.stderr)
            sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing is not None:
            existing.password_hash = hash_password(password)
            db.commit()
            print(f"Updated password for existing user '{username}'")
            return

        db.add(User(username=username, password_hash=hash_password(password)))
        db.commit()
        print(f"Created user '{username}'")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user_parser = subparsers.add_parser("create-user", help="Create or update the panel admin user")
    create_user_parser.add_argument("--username", required=True)
    create_user_parser.add_argument("--password", default=None, help="If omitted, prompts interactively")

    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.username, args.password)


if __name__ == "__main__":
    main()
