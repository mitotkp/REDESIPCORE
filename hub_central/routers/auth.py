import logging
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from jose import jwt
from dotenv import load_dotenv

from hub_central.helpers.encryption import Encriptacion
from hub_central.helpers.connection_helper import construir_url_desde_config
from hub_central.helpers.jsonsPath import obtener_json_path
from hub_central.helpers.audit import auditar
from hub_central.database.database import get_db
from hub_central.database.models import RefreshToken
from hub_central.classes.models import CredencialesLogin, RefreshTokenRequest, LogoutRequest

load_dotenv()

logger     = logging.getLogger(__name__)
_api_key   = os.getenv("SECRET_KEY")
_algoritmo = os.getenv("ALGORITHM")

_ACCESS_HOURS   = 8
_REFRESH_DAYS   = 7

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])


def _generar_access_token(sub: str, usuario: str, servidor_id: str) -> str:
    payload = {
        "sub":         sub,
        "usuario":     usuario,
        "servidor_id": servidor_id,
        "exp":         datetime.utcnow() + timedelta(hours=_ACCESS_HOURS),
    }
    return jwt.encode(payload, _api_key, algorithm=_algoritmo)


@router.post("/login")
async def login_de_usuario(
    datos: CredencialesLogin,
    db: Session = Depends(get_db),
):
    servers_config  = obtener_json_path()
    servidor_config = servers_config["servidores"].get(datos.servidor)

    if not servidor_config:
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    hub_user = servidor_config.get("hub_user")
    hub_pass = servidor_config.get("hub_pass")

    if not hub_user or not hub_pass:
        raise HTTPException(status_code=500, detail="El servidor no tiene configurada una cuenta de servicio")

    consulta = text("""
        SELECT CODUSUARIO, USUARIO, FECHACADUCIDADPASS, NEWPASS, BLOQUEADO, DESCATALOGADO
        FROM USUARIOS
        WHERE UPPER(NEWPASS) = UPPER(:pass)
    """)

    try:
        engine = create_engine(construir_url_desde_config(servidor_config), pool_pre_ping=True)
        with engine.connect() as conn:
            fila = conn.execute(consulta, {"pass": Encriptacion.encriptar(datos.password)}).fetchone()

            if not fila:
                raise HTTPException(status_code=401, detail="Contraseña incorrecta")
            if fila.BLOQUEADO == "T" or fila.DESCATALOGADO == "T":
                raise HTTPException(status_code=403, detail="El usuario está bloqueado o descatalogado")

            sub     = str(fila.CODUSUARIO)
            usuario = fila.USUARIO

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al autenticar contra '{datos.servidor}': {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")

    access_token  = _generar_access_token(sub, usuario, datos.servidor)
    refresh_token = RefreshToken.generar()

    # Limpiar tokens expirados del mismo usuario antes de guardar el nuevo
    db.query(RefreshToken).filter(
        RefreshToken.cod_usuario == sub,
        RefreshToken.expires_at  <  datetime.utcnow(),
    ).delete()

    db.add(RefreshToken(
        token       = refresh_token,
        cod_usuario = sub,
        servidor_id = datos.servidor,
        usuario     = usuario,
        expires_at  = datetime.utcnow() + timedelta(days=_REFRESH_DAYS),
    ))
    db.commit()

    auditar(db, {"sub": sub, "servidor_id": datos.servidor}, "LOGIN", f"usuario={usuario}")
    logger.info(f"Login exitoso — usuario={usuario} servidor={datos.servidor}")

    return {
        "status":        "success",
        "message":       "Login exitoso",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
    }


@router.post("/refresh")
async def refresh_token(
    datos: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    rt = db.query(RefreshToken).filter(
        RefreshToken.token    == datos.refresh_token,
        RefreshToken.revocado == False,
    ).first()

    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado.")

    # Limpiar tokens expirados del mismo usuario
    db.query(RefreshToken).filter(
        RefreshToken.cod_usuario == rt.cod_usuario,
        RefreshToken.expires_at  <  datetime.utcnow(),
    ).delete()
    db.commit()

    new_access = _generar_access_token(rt.cod_usuario, rt.usuario, rt.servidor_id)

    auditar(db, {"sub": rt.cod_usuario, "servidor_id": rt.servidor_id}, "TOKEN_REFRESH")
    logger.info(f"Token renovado — usuario={rt.usuario}")

    return {
        "status":       "success",
        "access_token": new_access,
        "token_type":   "bearer",
    }


@router.post("/logout")
async def logout(
    datos: LogoutRequest,
    db: Session = Depends(get_db),
):
    rt = db.query(RefreshToken).filter(RefreshToken.token == datos.refresh_token).first()
    if rt:
        rt.revocado = True
        db.commit()
        auditar(db, {"sub": rt.cod_usuario, "servidor_id": rt.servidor_id}, "LOGOUT")
        logger.info(f"Logout — usuario={rt.usuario}")

    return {"status": "success", "mensaje": "Sesión cerrada correctamente."}
