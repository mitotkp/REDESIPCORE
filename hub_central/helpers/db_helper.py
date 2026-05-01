import urllib.parse
from fastapi import  HTTPException
from sqlalchemy import create_engine, text
from pathlib import Path
from typing import Optional
from hub_central.helpers.jsonsPath import obtener_json_path

def ejecutar_consulta(servidor_destino: str, consulta_sql: str, parametros: Optional[dict] = None, bd_destino: Optional[str] = None):
    servers_config = obtener_json_path()
    servidor_config = servers_config["servidores"].get(servidor_destino)

    if not servidor_config:
        raise HTTPException(status_code=404, detail="Servidor no registrado")
    
    hub_user = servidor_config.get("hub_user")
    hub_pass = servidor_config.get("hub_pass")
    
    if not hub_user or not hub_pass:
        raise HTTPException(status_code=500, detail="El servidor no tiene configurada una cuenta de servicio")
    
    password_db_segura = urllib.parse.quote_plus(hub_pass)
    driver_formateado = servidor_config.get('driver', 'SQL Server').replace(' ', '+')

    if bd_destino == None: 
        bd_destino = "GENERAL"

    url_conexion = f"{servidor_config['tipo']}://{hub_user}:{password_db_segura}@{servidor_config['host']}:{servidor_config['puerto']}/{bd_destino}?driver={driver_formateado}&TrustServerCertificate=yes"
    
    sql = text(consulta_sql)

    print(f"Parámetros detectados en SQL: {sql.compile().params}")

    try: 
        engine = create_engine(url_conexion, pool_pre_ping=True)
        with engine.connect() as conn: 
            if parametros: 
                resultado = conn.execute(sql, parametros)
            else: 
                resultado = conn.execute(sql)
        
            return resultado.mappings().all()  
    except Exception as e: 
        print(f"Error de la base de datos: {e}")
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
