import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

_host = os.getenv("MYSQL_HOST", "localhost")
_port = os.getenv("MYSQL_PORT", "3306")
_db   = os.getenv("MYSQL_DB",   "redesipcore_hub")
_user = os.getenv("MYSQL_USER", "")
_pass = urllib.parse.quote_plus(os.getenv("MYSQL_PASS", ""))

MYSQL_URL = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/{_db}"

engine = create_engine(MYSQL_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
