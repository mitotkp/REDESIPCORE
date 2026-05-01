import os
import time
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

_host = os.getenv("MYSQL_HOST", "localhost")
_port = os.getenv("MYSQL_PORT", "3306")
_db   = os.getenv("MYSQL_DB",   "redesipcore_hub")
_user = os.getenv("MYSQL_USER", "")
_pass = urllib.parse.quote_plus(os.getenv("MYSQL_PASS", ""))

MYSQL_URL = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/{_db}"

Base = declarative_base()


def _crear_db_si_no_existe(max_intentos: int = 5, espera: int = 3) -> None:
    """
    Conecta a MySQL sin especificar base de datos y la crea si no existe.
    Reintenta hasta max_intentos veces para tolerar el arranque lento de Docker.
    """
    url_sin_db = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/"
    for intento in range(1, max_intentos + 1):
        try:
            tmp_engine = create_engine(url_sin_db, pool_pre_ping=True)
            with tmp_engine.connect() as conn:
                conn.execute(text(
                    f"CREATE DATABASE IF NOT EXISTS `{_db}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                ))
            tmp_engine.dispose()
            print(f"[REDESIPCORE] Base de datos '{_db}' lista.")
            return
        except Exception as e:
            if intento == max_intentos:
                raise RuntimeError(
                    f"[REDESIPCORE] No se pudo conectar a MySQL tras {max_intentos} intentos: {e}"
                )
            print(f"[REDESIPCORE] MySQL no disponible, reintento {intento}/{max_intentos} en {espera}s...")
            time.sleep(espera)


_crear_db_si_no_existe()

engine       = create_engine(MYSQL_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
