import re
from urllib.parse import urlparse, urlunparse, quote
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, NullPool
from core.config import settings


def _fix_supabase_url(url: str) -> str:
    """
    psycopg v3 has a known bug parsing Supabase connection strings where the
    username contains dots (e.g. postgres.hwfjlxfbabcavigutimz). It interprets
    the part before the dot as a tenant and fails with ENOTFOUND.

    Fix: URL-encode the username portion so the dot becomes %2E and psycopg
    parses the full string as a single username.

    Also normalises the scheme to postgresql+psycopg for psycopg v3.
    """
    # Normalise scheme first (remove driver prefix if any)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    # Parse the plain postgresql:// URL
    parsed = urlparse(url)
    username = parsed.username or ""

    if "." in username:
        # URL-encode the dot so psycopg v3 doesn't split on it as tenant/user
        encoded_user = quote(username, safe="")
        password_part = f":{quote(parsed.password or '', safe='')}" if parsed.password else ""
        host_part = parsed.hostname or ""
        port_part = f":{parsed.port}" if parsed.port else ""
        new_netloc = f"{encoded_user}{password_part}@{host_part}{port_part}"
        parsed = parsed._replace(netloc=new_netloc)
        url = urlunparse(parsed)

    # Ensure psycopg v3 driver
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _fix_supabase_url(settings.DATABASE_URL)

is_sqlite = DATABASE_URL.startswith("sqlite")
is_pooler = ":6543" in DATABASE_URL

if is_sqlite:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    connect_args = {}
    if "amazonaws.com" in DATABASE_URL or "supabase.com" in DATABASE_URL:
        connect_args["sslmode"] = "require"

    if is_pooler:
        # Use NullPool when using Supabase transaction pooler (PgBouncer)
        connect_args["prepare_threshold"] = None
        engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args=connect_args
        )
    else:
        # Standard QueuePool for direct connections (5432)
        engine = create_engine(
            DATABASE_URL,
            pool_size=3,
            max_overflow=7,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args=connect_args
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
