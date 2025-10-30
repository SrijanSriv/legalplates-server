from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/legalplates")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections every hour
    pool_timeout=30,     # Timeout for getting connection from pool
    max_overflow=10,     # Additional connections beyond pool_size
    pool_size=5,         # Base number of connections to maintain
    echo=False           # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback on any exception to prevent connection issues
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    from app.models import Template, TemplateVariable, Instance, Document
    Base.metadata.create_all(bind=engine, tables=[Template.__table__, TemplateVariable.__table__, Instance.__table__, Document.__table__])
