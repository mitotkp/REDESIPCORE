import json 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
servers_path = f"{BASE_DIR}/jsons/connections.json"

servers_config = {"servidores": {}} 

def obtener_json_path():
    try: 
        with open(servers_path, "r", encoding="utf-8") as f: 
            servers_config = json.load(f)
            print(servers_config)
            print("JSON cargado exitosamente")
            return servers_config
    except FileNotFoundError: 
        print(f"Aviso: Archivo no encontrado en {servers_path}. Se creará al registrar el primer servidor.")
