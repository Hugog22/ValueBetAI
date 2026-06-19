from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, NullPool
from core.config import settings

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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

