"""Tests de gestión de servidores y listado de empresas."""
from unittest.mock import patch, MagicMock
from tests.conftest import ADMIN_HEADERS


# ── Listar servidores ─────────────────────────────────────────────────────────

def test_listar_servidores_sin_datos(client):
    with patch("hub_central.routers.servidores.obtener_json_path",
               return_value={"servidores": {}}):
        r = client.get("/api/servidores/")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_listar_servidores_con_datos(client):
    mock_config = {"servidores": {"local": {}, "remoto": {}}}
    with patch("hub_central.routers.servidores.obtener_json_path", return_value=mock_config):
        r = client.get("/api/servidores/")
    body = r.json()
    assert body["total"] == 2
    assert "local" in body["servidores_disponibles"]


# ── Registrar servidor ────────────────────────────────────────────────────────

def test_registrar_servidor_sin_admin_key_retorna_403(client):
    r = client.post("/api/servidores/registrar", json={
        "servidor": "nuevo", "host": "10.0.0.1", "puerto": 1433,
        "tipo": "mssql", "usuario": "sa", "password": "pass"
    })
    assert r.status_code == 403


def test_registrar_servidor_duplicado_retorna_400(client):
    config_existente = {"servidores": {"existente": {"host": "x"}}}
    with patch("hub_central.routers.servidores.obtener_json_path",
               return_value=config_existente):
        r = client.post("/api/servidores/registrar", json={
            "servidor": "existente", "host": "10.0.0.1", "puerto": 1433,
            "tipo": "mssql", "usuario": "sa", "password": "pass"
        }, headers=ADMIN_HEADERS)
    assert r.status_code == 400


def test_registrar_servidor_conexion_fallida_retorna_400(client):
    with patch("hub_central.routers.servidores.obtener_json_path",
               return_value={"servidores": {}}), \
         patch("hub_central.routers.servidores.create_engine",
               side_effect=Exception("Connection refused")):
        r = client.post("/api/servidores/registrar", json={
            "servidor": "nuevo", "host": "10.0.0.1", "puerto": 1433,
            "tipo": "mssql", "usuario": "sa", "password": "pass"
        }, headers=ADMIN_HEADERS)
    assert r.status_code == 400


# ── Listar empresas ───────────────────────────────────────────────────────────

def test_listar_empresas_paginado(client):
    empresas_mock = [
        {"CODEMPRESA": str(i), "TITULO": f"Empresa {i}", "PATHBD": "", "PAIS": "VE"}
        for i in range(25)
    ]
    with patch("hub_central.routers.servidores.ejecutar_consulta",
               return_value=empresas_mock):
        r = client.get("/api/servidores/listarEmpresas?pagina=1&tamano=10")

    assert r.status_code == 200
    body = r.json()
    assert body["total"]   == 25
    assert body["paginas"] == 3
    assert len(body["empresas"]) == 10


def test_listar_empresas_segunda_pagina(client):
    empresas_mock = [
        {"CODEMPRESA": str(i), "TITULO": f"Empresa {i}", "PATHBD": "", "PAIS": "VE"}
        for i in range(25)
    ]
    with patch("hub_central.routers.servidores.ejecutar_consulta",
               return_value=empresas_mock):
        r = client.get("/api/servidores/listarEmpresas?pagina=3&tamano=10")

    assert r.status_code == 200
    assert len(r.json()["empresas"]) == 5  # últimas 5


# ── Estado de la API ──────────────────────────────────────────────────────────

def test_root_en_linea(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "version" in r.json()
