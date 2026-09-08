import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Defaults to a local SQLite file so the app runs with zero DB setup.
# To use Postgres instead, set DATABASE_URL, e.g.:
#   export DATABASE_URL="postgresql://kyc_user:kyc_pass@localhost:5432/kyc_poc"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///kyc_poc.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db():
    from app.models import Base
    Base.metadata.create_all(bind=engine)
