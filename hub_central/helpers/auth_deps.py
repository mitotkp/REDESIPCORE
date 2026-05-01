import os
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

_api_key   = os.getenv("SECRET_KEY")
_algoritmo = os.getenv("ALGORITHM")
_security  = HTTPBearer()


def obtener_payload(
    credenciales: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    token = credenciales.credentials
    try:
        return jwt.decode(token, _api_key, algorithms=[_algoritmo])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o corrupto.")


def verificar_admin(x_admin_key: str | None = Header(default=None)) -> None:
    admin_secret = os.getenv("ADMIN_SECRET")
    if not admin_secret or x_admin_key != admin_secret:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Se requiere clave de administrador.",
        )
