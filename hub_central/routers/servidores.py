import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from jose import jwt
from dotenv import load_dotenv
from hub_central.classes.models import ServidorRegistro
from hub_central.helpers.db_helper import ejecutar_consulta
from hub_central.helpers.jsonsPath import obtener_json_path
from hub_central.helpers.connection_helper import construir_url_conexion, construir_url_desde_config

load_dotenv()

api_key   = os.getenv("SECRET_KEY")
algoritmo = os.getenv("ALGORITHM")

security_scheme = HTTPBearer()

router = APIRouter(
    prefix="/api/servidores",
    tags=["Servidores"]
)

# Ruta del archivo de configuración
_BASE_DIR    = Path(__file__).resolve().parent.parent
_SERVERS_PATH = _BASE_DIR / "jsons" / "connections.json"


def _guardar_config(config: dict) -> None:
    _SERVERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SERVERS_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


@router.get("/")
async def listar_servidores():
    servers_config = obtener_json_path()
    nombres = list(servers_config["servidores"].keys())
    return {"total": len(nombres), "servidores_disponibles": nombres}


@router.post("/registrar")
async def registrar_servidor(datos: ServidorRegistro):
    servers_config = obtener_json_path()

    if datos.servidor in servers_config["servidores"]:
        raise HTTPException(status_code=400, detail="Ya existe un servidor con ese identificador")

    if not datos.db_name:
        datos.db_name = "GENERAL"

    url_prueba = construir_url_conexion(
        tipo=datos.tipo,
        host=datos.host,
        puerto=datos.puerto,
        db_name=datos.db_name,
        usuario=datos.usuario,
        password=datos.password,
        driver=datos.driver,
    )

    try:
        engine = create_engine(url_prueba, pool_pre_ping=True)
        with engine.connect():
            print(f"Test de conexión exitoso para: {datos.servidor}")
    except Exception as e:
        print(f"Error de conexión: {e}")
        raise HTTPException(
            status_code=400,
            detail="La prueba de conexión falló. Revisa las credenciales o el host.",
        )

    nuevo = {
        "host":     datos.host,
        "puerto":   datos.puerto,
        "db_name":  datos.db_name,
        "tipo":     datos.tipo,
        "hub_user": datos.usuario,
        "hub_pass": datos.password,
    }
    if datos.driver:
        nuevo["driver"] = datos.driver

    servers_config["servidores"][datos.servidor] = nuevo
    _guardar_config(servers_config)

    return {
        "status":  "success",
        "mensaje": f"Servidor '{datos.servidor}' verificado y registrado correctamente.",
    }


@router.post("/login")
async def iniciar_sesion(server: str, user: str, password: str):
    servers_config = obtener_json_path()
    servidor = servers_config["servidores"].get(server)

    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    url = construir_url_conexion(
        tipo=servidor["tipo"],
        host=servidor["host"],
        puerto=servidor["puerto"],
        db_name=servidor["db_name"],
        usuario=user,
        password=password,
        driver=servidor.get("driver"),
    )

    try:
        engine = create_engine(url)
        with engine.connect():
            return {"status": "success", "mensaje": "Autenticado en la DB remota"}
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas en el servidor remoto")


@router.get("/listarEmpresas")
async def listar_empresas(credenciales: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credenciales.credentials
    try:
        payload  = jwt.decode(token, api_key, algorithms=[algoritmo])
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
        return {"status": "success", "empresas": empresas}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o corrupto.")


@router.get("/listarEmpresasUsuario")
async def listar_empresa_usuario(credenciales: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credenciales.credentials
    try:
        payload     = jwt.decode(token, api_key, algorithms=[algoritmo])
        servidor    = payload["servidor_id"]
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
        empresas_usuario = ejecutar_consulta(servidor, query, {"codUsuario": cod_usuario})
        return {"status": "success", "empresas": empresas_usuario}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o corrupto.")
