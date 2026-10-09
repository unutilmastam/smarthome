"""Admin CLI (runs in cPanel Terminal).

    python -m app.cli create-owner --email you@example.com --name "Ism" --home-name "Uy"

The password is read interactively (twice) or from stdin with --password-stdin.
There is no public registration: this is how the first owner is created.
"""

import argparse
import getpass
import sys
import uuid
from typing import List, Optional

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_secret
from app.db.session import Database
from app.models import Home, HomeMember, User
from app.schemas.auth import PASSWORD_MIN, normalize_email
from app.services import audit


class CliError(Exception):
    pass


def create_owner(db, email: str, name: str, password: str, home_name: str,
                 timezone: str = "Asia/Tashkent") -> Home:
    email = normalize_email(email)
    if len(password) < PASSWORD_MIN:
        raise CliError(f"Password must be at least {PASSWORD_MIN} characters")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(id=uuid.uuid4(), email=email, name=name, password_hash=hash_secret(password))
        db.add(user)
        db.flush()
    else:
        # Re-running the installer (or a forgotten password): the terminal sets it again and
        # the existing home is kept instead of a second, empty one being created.
        user.password_hash = hash_secret(password)
        owned = db.scalar(select(Home).join(HomeMember, HomeMember.home_id == Home.id)
                          .where(HomeMember.user_id == user.id, HomeMember.role == "owner"))
        if owned is not None:
            audit.record(db, "user.password_reset", actor_type="system", actor_id=user.id,
                         home_id=owned.id, target_type="user", target_id=user.id,
                         details={"via": "cli"})
            db.commit()
            return owned
    home = Home(id=uuid.uuid4(), name=home_name, timezone=timezone)
    db.add(home)
    db.flush()
    db.add(HomeMember(home_id=home.id, user_id=user.id, role="owner"))
    audit.record(db, "home.created", actor_type="system", actor_id=user.id, home_id=home.id,
                 target_type="home", target_id=home.id, details={"via": "cli"})
    db.commit()
    return home


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    co = sub.add_parser("create-owner", help="Create a user and a home owned by them")
    co.add_argument("--email", required=True)
    co.add_argument("--name", required=True)
    co.add_argument("--home-name", default="Uy")
    co.add_argument("--timezone", default="Asia/Tashkent")
    co.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args(argv)

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match", file=sys.stderr)
            return 2

    database = Database(get_settings())
    db = next(database.session())
    try:
        home = create_owner(db, args.email, args.name, password, args.home_name, args.timezone)
    except (CliError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"Owner created. home_id={home.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
