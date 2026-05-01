import json 
import urllib.parse
from fastapi import  APIRouter, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from jose import jwt
from hub_central.helpers.encryption import Encriptacion
from hub_central.classes.models import CredencialesLogin
from hub_central.helpers.jsonsPath import servers_config, servers_path, obtener_json_path
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SECRET_KEY")
algoritmo = os.getenv("ALGORITHM")

security_scheme = HTTPBearer()

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticacion"]
)

servers_config = obtener_json_path()

@router.post("/login")
async def login_de_usuario(datos: CredencialesLogin):

    servidor_config = servers_config["servidores"].get(datos.servidor)
    if not servidor_config: 
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    hub_user = servidor_config.get("hub_user")
    hub_pass = servidor_config.get("hub_pass")

    if not hub_user or not hub_pass: 
        raise HTTPException(status_code=500, detail="El servidor no tiene configurada una cuenta de servicio")

    password_db_segura = urllib.parse.quote_plus(hub_pass)
    driver_formateado = servidor_config.get('driver', 'SQL Server').replace(' ', '+')

    url_conexion = f"{servidor_config['tipo']}://{hub_user}:{password_db_segura}@{servidor_config['host']}:{servidor_config['puerto']}/{servidor_config['db_name']}?driver={driver_formateado}&TrustServerCertificate=yes"

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
            resultado = conn.execute(consulta_sql, {"pass": Encriptacion.encriptar(datos.password)}).fetchone()

            if not resultado: 
                raise HTTPException(status_code=401, detail="Contraseña incorrecta")
            if resultado.BLOQUEADO == 'T' or resultado.DESCATALOGADO == 'T':
                raise HTTPException(status_code=403, detail="El usuario esta bloqueado")
            
            payload = {
                "sub": str(resultado.CODUSUARIO), 
                "usuario": resultado.USUARIO, 
                "servidor_id": datos.servidor, 
                "exp": datetime.utcnow() + timedelta(hours=8) 
            }

            token = jwt.encode(payload, api_key, algorithm=algoritmo)

            return {
                "status": "success", 
                "message": "login exitoso", 
                "access_token": token, 
                "token_type": "bearer"
            }
    
    except HTTPException:
        raise

    except Exception as e: 
        print(f"Error de la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
