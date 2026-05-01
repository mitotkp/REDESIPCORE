"""
Configuración global de tests.
Las variables de entorno se establecen ANTES de importar cualquier módulo
del hub para que los valores de module-level sean correctos.
"""
import os

os.environ.setdefault("TESTING",      "true")
os.environ.setdefault("SECRET_KEY",   "clave_secreta_para_tests_1234567890")
os.environ.setdefault("ALGORITHM",    "HS256")
os.environ.setdefault("ADMIN_SECRET", "admin_key_tests")
os.environ.setdefault("MYSQL_HOST",   "localhost")
os.environ.setdefault("MYSQL_PORT",   "3306")
os.environ.setdefault("MYSQL_DB",     "test_hub")
os.environ.setdefault("MYSQL_USER",   "test")
os.environ.setdefault("MYSQL_PASS",   "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from hub_central.database.database import Base, get_db
from hub_central.helpers.auth_deps import obtener_payload

# ── Base de datos SQLite en memoria para tests ─────────────────────────────────

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


@pytest.fixture(scope="session", autouse=True)
def crear_tablas():
    """Crea todas las tablas en SQLite una vez por sesión de test."""
    import hub_central.database.models  # noqa: F401
    Base.metadata.create_all(_TEST_ENGINE)
    yield
    Base.metadata.drop_all(_TEST_ENGINE)


@pytest.fixture
def db():
    """Sesión de BD por test; hace rollback al terminar."""
    session = _TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# Payload de usuario de prueba
MOCK_PAYLOAD  = {"sub": "U001", "usuario": "testuser", "servidor_id": "local"}
ADMIN_KEY     = os.environ["ADMIN_SECRET"]
ADMIN_HEADERS = {"X-Admin-Key": ADMIN_KEY}


@pytest.fixture
def client(db):
    """TestClient con BD SQLite y payload JWT fijo."""
    app.dependency_overrides[get_db]           = lambda: db
    app.dependency_overrides[obtener_payload]  = lambda: MOCK_PAYLOAD

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()
