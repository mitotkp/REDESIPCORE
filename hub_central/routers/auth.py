import os
from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv
from hub_central.helpers.encryption import Encriptacion
from hub_central.helpers.connection_helper import construir_url_desde_config
from hub_central.classes.models import CredencialesLogin
from hub_central.helpers.jsonsPath import obtener_json_path

load_dotenv()

api_key   = os.getenv("SECRET_KEY")
algoritmo = os.getenv("ALGORITHM")

security_scheme = HTTPBearer()

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticacion"]
)

@router.post("/login")
async def login_de_usuario(datos: CredencialesLogin):
    servers_config  = obtener_json_path()
    servidor_config = servers_config["servidores"].get(datos.servidor)

    if not servidor_config:
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    hub_user = servidor_config.get("hub_user")
    hub_pass = servidor_config.get("hub_pass")

    if not hub_user or not hub_pass:
        raise HTTPException(
            status_code=500,
            detail="El servidor no tiene configurada una cuenta de servicio",
        )

    url_conexion = construir_url_desde_config(servidor_config)

    consulta_sql = text("""
        SELECT
            CODUSUARIO,
            USUARIO,
            FECHACADUCIDADPASS,
            NEWPASS,
            BLOQUEADO,
            DESCATALOGADO
        FROM
            USUARIOS
        WHERE
            UPPER(NEWPASS) = UPPER(:pass)
    """)

    try:
        engine = create_engine(url_conexion, pool_pre_ping=True)
        with engine.connect() as conn:
            resultado = conn.execute(
                consulta_sql, {"pass": Encriptacion.encriptar(datos.password)}
            ).fetchone()

            if not resultado:
                raise HTTPException(status_code=401, detail="Contraseña incorrecta")
            if resultado.BLOQUEADO == "T" or resultado.DESCATALOGADO == "T":
                raise HTTPException(status_code=403, detail="El usuario esta bloqueado")

            payload = {
                "sub":         str(resultado.CODUSUARIO),
                "usuario":     resultado.USUARIO,
                "servidor_id": datos.servidor,
                "exp":         datetime.utcnow() + timedelta(hours=8),
            }

            token = jwt.encode(payload, api_key, algorithm=algoritmo)

            return {
                "status":       "success",
                "message":      "login exitoso",
                "access_token": token,
                "token_type":   "bearer",
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error de la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
