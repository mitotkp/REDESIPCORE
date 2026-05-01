from typing import Optional
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from hub_central.helpers.jsonsPath import obtener_json_path
from hub_central.helpers.connection_helper import construir_url_desde_config


def ejecutar_consulta(
    servidor_destino: str,
    consulta_sql: str,
    parametros: Optional[dict] = None,
    bd_destino: Optional[str] = None,
):
    servers_config = obtener_json_path()
    servidor_config = servers_config["servidores"].get(servidor_destino)

    if not servidor_config:
        raise HTTPException(status_code=404, detail="Servidor no registrado")

    hub_user = servidor_config.get("hub_user")
    hub_pass = servidor_config.get("hub_pass")

    if not hub_user or not hub_pass:
        raise HTTPException(
            status_code=500,
            detail="El servidor no tiene configurada una cuenta de servicio",
        )

    url_conexion = construir_url_desde_config(servidor_config, bd_destino)
    sql = text(consulta_sql)

    try:
        engine = create_engine(url_conexion, pool_pre_ping=True)
        with engine.connect() as conn:
            resultado = conn.execute(sql, parametros) if parametros else conn.execute(sql)
            return resultado.mappings().all()
    except Exception as e:
        print(f"Error de la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
