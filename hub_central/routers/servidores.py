import json 
import urllib.parse
from fastapi import  APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from jose import jwt
from hub_central.classes.models import ServidorRegistro
from hub_central.helpers.db_helper import ejecutar_consulta
from hub_central.helpers.jsonsPath import servers_config, servers_path, obtener_json_path
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("SECRET_KEY")
algoritmo = os.getenv("ALGORITHM")

security_scheme = HTTPBearer()

servers_config = obtener_json_path()

router = APIRouter(
    prefix="/api/servidores",
    tags=["Autenticacion"]
)

@router.get("/")
async def listar_servidores():
    nombres = list(servers_config["servidores"].keys())
    return {"total": len(nombres), "servidores_disponibles": nombres}

@router.post("/registrar")
async def registrar_servidor(datos: ServidorRegistro):
    
    if datos.servidor in servers_config["servidores"]:
        raise HTTPException(status_code=400, detail="Ya existe un servidor con ese identificador")

    if datos.db_name == "":
        datos.db_name = 'GENERAL' 
    
    password_segura = urllib.parse.quote_plus(datos.password)
    url_prueba = f"{datos.tipo}://{datos.usuario}:{password_segura}@{datos.host}:{datos.puerto}/{datos.db_name}"
    
    if datos.driver:
        driver_formateado = datos.driver.replace(' ', '+')
        url_prueba += f"?driver={driver_formateado}&TrustServerCertificate=yes"

    try: 
        engine = create_engine(url_prueba, pool_pre_ping=True)
        with engine.connect() as conn: 
            print(f"Test de conexión exitoso para: {datos.servidor}")
    except Exception as e:
        print(f"Error de conexión: {e}")
        raise HTTPException(status_code=400, detail="La prueba de conexión falló. Revisa las credenciales o el host.")

    nuevo_servidor_data = {
        "host": datos.host,
        "puerto": datos.puerto,
        "db_name": datos.db_name,
        "tipo": datos.tipo
    }
    if datos.driver:
        nuevo_servidor_data["driver"] = datos.driver

    servers_config["servidores"][datos.servidor] = nuevo_servidor_data

    servers_path.parent.mkdir(parents=True, exist_ok=True)
    with open(servers_path, 'w', encoding='utf-8') as file: 
        json.dump(servers_config, file, indent=4)

    return {
        "status": "success", 
        "mensaje": f"Servidor '{datos.servidor}' verificado y registrado correctamente."
    }

@router.post("/login")
async def iniciar_sesion(server: str, user: str, password: str):
    servidor = servers_config["servidores"].get(server)
    if not servidor: 
        raise HTTPException(status_code=404, detail="Servidor no registrado")
    
    password_segura = urllib.parse.quote_plus(password)
    url = f"{servidor['tipo']}://{user}:{password_segura}@{servidor['host']}:{servidor['puerto']}/{servidor['db_name']}"

    if "driver" in servidor:
        driver_formateado = servidor['driver'].replace(' ', '+')
        url += f"?driver={driver_formateado}&TrustServerCertificate=yes"

    try: 
        engine = create_engine(url)
        with engine.connect() as conn: 
            return {"status": "success", "mensaje": "Autenticado en la DB remota"}
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas en el servidor remoto")

@router.get('/listarEmpresas')
async def listar_empresas(credenciales: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credenciales.credentials

    try: 
        payload = jwt.decode(token, api_key, algorithms=[algoritmo])

        servidor = payload["servidor_id"]

        query = """
            SELECT 
                CODEMPRESA
                , TITULO
                , PATHBD
                , PAIS
            FROM 
                EMPRESAS
        """
        empresas = ejecutar_consulta(servidor, query)

        print(empresas)

        return {
            "status": "success", 
            "empresas": empresas
        }

    except jwt.ExpiredSignatureError: 
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o corrupto.")

@router.get('/listarEmpresasUsuario')
async def listar_empresa_usuario(credenciales: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credenciales.credentials

    try: 
        payload = jwt.decode(token, api_key, algorithms=[algoritmo])

        servidor = payload["servidor_id"]
        cod_usuario = payload["sub"]

        query = """
            SELECT DISTINCT 
                EU.CODEMPRESA,
                EU.CODUSUARIO,
                E.TITULO, 
                E.PATHBD,
                E.PAIS
            FROM 
                EMPRESASUSUARIO EU
                INNER JOIN EMPRESAS E ON E.CODEMPRESA = EU.CODEMPRESA
            WHERE
                EU.CODUSUARIO = :codUsuario
        """

        mis_parametros = {
            "codUsuario": cod_usuario
        }

        empresas_usuario = ejecutar_consulta(servidor, query, mis_parametros)

        print(empresas_usuario)

        return {
            "status" : "success", 
            "empresas": empresas_usuario
        }

    except jwt.ExpiredSignatureError: 
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o corrupto.")

