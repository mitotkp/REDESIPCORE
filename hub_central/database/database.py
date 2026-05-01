import logging
import os
import time
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_host    = os.getenv("MYSQL_HOST", "localhost")
_port    = os.getenv("MYSQL_PORT", "3306")
_db      = os.getenv("MYSQL_DB",   "redesipcore_hub")
_user    = os.getenv("MYSQL_USER", "")
_pass    = urllib.parse.quote_plus(os.getenv("MYSQL_PASS", ""))
TESTING  = os.getenv("TESTING",   "false").lower() == "true"

MYSQL_URL = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/{_db}"

Base = declarative_base()

# El engine solo se crea si no estamos en modo test; en tests se inyecta
# un engine SQLite por medio de app.dependency_overrides[get_db].
if not TESTING:
    engine       = create_engine(MYSQL_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine       = None  # type: ignore[assignment]
    SessionLocal = None  # type: ignore[assignment]


def _crear_db_si_no_existe(max_intentos: int = 10, espera: int = 3) -> None:
    url_sin_db = f"mysql+pymysql://{_user}:{_pass}@{_host}:{_port}/"
    for intento in range(1, max_intentos + 1):
        try:
            tmp = create_engine(url_sin_db)
            with tmp.connect() as conn:
                conn.execute(text(
                    f"CREATE DATABASE IF NOT EXISTS `{_db}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                ))
            tmp.dispose()
            logger.info(f"Base de datos '{_db}' lista.")
            return
        except Exception as e:
            if intento == max_intentos:
                raise RuntimeError(
                    f"No se pudo conectar a MySQL tras {max_intentos} intentos: {e}"
                )
            logger.warning(
                f"MySQL no disponible — reintento {intento}/{max_intentos} en {espera}s..."
            )
            time.sleep(espera)


def inicializar_db() -> None:
    """Crea la BD MySQL si no existe y aplica el esquema de tablas."""
    _crear_db_si_no_existe()
    import hub_central.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Esquema de tablas verificado/creado.")


def get_db():
    if SessionLocal is None:
        raise RuntimeError("get_db llamado en modo TESTING sin override configurado.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
