"""Tests de autenticación: refresh token y logout."""
from datetime import datetime, timedelta
from hub_central.database.models import RefreshToken


def _crear_refresh_token(db, cod_usuario="U001", servidor_id="local",
                          usuario="testuser", dias=7, revocado=False) -> str:
    token = RefreshToken.generar()
    db.add(RefreshToken(
        token=token, cod_usuario=cod_usuario, servidor_id=servidor_id,
        usuario=usuario, expires_at=datetime.utcnow() + timedelta(days=dias),
        revocado=revocado,
    ))
    db.commit()
    return token


# ── /api/auth/refresh ─────────────────────────────────────────────────────────

def test_refresh_token_inexistente_retorna_401(client):
    r = client.post("/api/auth/refresh", json={"refresh_token": "token_falso"})
    assert r.status_code == 401


def test_refresh_token_revocado_retorna_401(client, db):
    token = _crear_refresh_token(db, revocado=True)
    r = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 401


def test_refresh_token_expirado_retorna_401(client, db):
    token = _crear_refresh_token(db, dias=-1)
    r = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 401


def test_refresh_token_valido_retorna_access_token(client, db):
    token = _crear_refresh_token(db)
    r = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "access_token" in body
    assert body["token_type"] == "bearer"


# ── /api/auth/logout ──────────────────────────────────────────────────────────

def test_logout_revoca_el_token(client, db):
    token = _crear_refresh_token(db)
    r = client.post("/api/auth/logout", json={"refresh_token": token})
    assert r.status_code == 200

    # Confirma que ya no sirve para refrescar
    r2 = client.post("/api/auth/refresh", json={"refresh_token": token})
    assert r2.status_code == 401


def test_logout_token_inexistente_no_falla(client):
    """Cerrar sesión con un token que no existe no debe lanzar error."""
    r = client.post("/api/auth/logout", json={"refresh_token": "no_existe"})
    assert r.status_code == 200
