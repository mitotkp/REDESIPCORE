import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hub_central.classes.models import ServidorRegistro
from hub_central.database.database import get_db
from hub_central.helpers.db_helper import ejecutar_consulta
from hub_central.helpers.jsonsPath import obtener_json_path
from hub_central.helpers.connection_helper import construir_url_conexion
from hub_central.helpers.auth_deps import obtener_payload, verificar_admin
from hub_central.helpers.audit import auditar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/servidores", tags=["Servidores"])

_SERVERS_PATH = Path(__file__).resolve().parent.parent / "jsons" / "connections.json"


def _guardar_config(config: dict) -> None:
    _SERVERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SERVERS_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


@router.get("/")
async def listar_servidores():
    nombres = list(obtener_json_path()["servidores"].keys())
    return {"total": len(nombres), "servidores_disponibles": nombres}


@router.post("/registrar")
async def registrar_servidor(
    datos: ServidorRegistro,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    servers_config = obtener_json_path()

    if datos.servidor in servers_config["servidores"]:
        raise HTTPException(status_code=400, detail="Ya existe un servidor con ese identificador")

    if not datos.db_name:
        datos.db_name = "GENERAL"

    url_prueba = construir_url_conexion(
        tipo=datos.tipo, host=datos.host, puerto=datos.puerto,
        db_name=datos.db_name, usuario=datos.usuario,
        password=datos.password, driver=datos.driver,
    )

    try:
        with create_engine(url_prueba, pool_pre_ping=True).connect():
            pass
    except Exception as e:
        logger.warning(f"Test de conexión fallido para '{datos.servidor}': {e}")
        raise HTTPException(status_code=400,
                            detail="La prueba de conexión falló. Revisa las credenciales o el host.")

    nuevo = {
        "host": datos.host, "puerto": datos.puerto, "db_name": datos.db_name,
        "tipo": datos.tipo, "hub_user": datos.usuario, "hub_pass": datos.password,
    }
    if datos.driver:
        nuevo["driver"] = datos.driver

    servers_config["servidores"][datos.servidor] = nuevo
    _guardar_config(servers_config)

    auditar(db, payload, "SERVIDOR_REGISTRADO", f"servidor={datos.servidor} tipo={datos.tipo}")
    logger.info(f"Servidor registrado: '{datos.servidor}' tipo={datos.tipo}")

    return {"status": "success", "mensaje": f"Servidor '{datos.servidor}' registrado correctamente."}


@router.post("/login")
async def iniciar_sesion(server: str, user: str, password: str):
    servidor = obtener_json_path()["servidores"].get(server)
    if not servidor:
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    url = construir_url_conexion(
        tipo=servidor["tipo"], host=servidor["host"], puerto=servidor["puerto"],
        db_name=servidor["db_name"], usuario=user, password=password,
        driver=servidor.get("driver"),
    )
    try:
        with create_engine(url).connect():
            return {"status": "success", "mensaje": "Autenticado en la DB remota"}
    except Exception:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas en el servidor remoto")


@router.get("/listarEmpresas")
async def listar_empresas(
    payload: dict = Depends(obtener_payload),
    pagina: int   = Query(1,  ge=1),
    tamano: int   = Query(20, ge=1, le=200),
):
    todas = ejecutar_consulta(
        payload["servidor_id"],
        "SELECT CODEMPRESA, TITULO, PATHBD, PAIS FROM EMPRESAS",
    )
    total = len(todas)
    skip  = (pagina - 1) * tamano
    page  = todas[skip: skip + tamano]

    return {
        "status":  "success",
        "total":   total,
        "pagina":  pagina,
        "tamano":  tamano,
        "paginas": (total + tamano - 1) // tamano if total else 0,
        "empresas": [dict(r) for r in page],
    }


@router.get("/listarEmpresasUsuario")
async def listar_empresa_usuario(
    payload: dict = Depends(obtener_payload),
    pagina: int   = Query(1,  ge=1),
    tamano: int   = Query(20, ge=1, le=200),
):
    query = """
        SELECT DISTINCT EU.CODEMPRESA, EU.CODUSUARIO, E.TITULO, E.PATHBD, E.PAIS
        FROM EMPRESASUSUARIO EU
        INNER JOIN EMPRESAS E ON E.CODEMPRESA = EU.CODEMPRESA
        WHERE EU.CODUSUARIO = :codUsuario
    """
    todas = ejecutar_consulta(payload["servidor_id"], query, {"codUsuario": payload["sub"]})
    total = len(todas)
    skip  = (pagina - 1) * tamano
    page  = todas[skip: skip + tamano]

    return {
        "status":  "success",
        "total":   total,
        "pagina":  pagina,
        "tamano":  tamano,
        "paginas": (total + tamano - 1) // tamano if total else 0,
        "empresas": [dict(r) for r in page],
    }
