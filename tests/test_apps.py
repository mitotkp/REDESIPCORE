"""Tests del catálogo de aplicaciones y visibilidad por rol."""
import json
import pytest
from pathlib import Path
from tests.conftest import ADMIN_HEADERS, MOCK_PAYLOAD
from hub_central.database.models import Departamento, UsuarioDepartamento


@pytest.fixture(autouse=True)
def apps_json_limpio(tmp_path, monkeypatch):
    """Usa un apps.json temporal vacío para cada test."""
    archivo = tmp_path / "apps.json"
    archivo.write_text(json.dumps({"apps": []}), encoding="utf-8")
    import hub_central.helpers.apps_helper as helper
    monkeypatch.setattr(helper, "apps_path", archivo)


# ── Crear app ─────────────────────────────────────────────────────────────────

def test_crear_app(client):
    r = client.post("/api/apps/", json={
        "name": "Sistema ERP", "version": "1.0",
        "href": "http://erp.local", "permissions": ["admin", "jefe"]
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 201
    assert r.json()["app"]["name"] == "Sistema ERP"


def test_crear_app_sin_admin_key_retorna_403(client):
    r = client.post("/api/apps/", json={
        "name": "App", "version": "1.0",
        "href": "http://app.local", "permissions": ["empleado"]
    })
    assert r.status_code == 403


def test_crear_app_duplicada_retorna_409(client):
    payload = {"name": "Duplicada", "version": "1.0",
               "href": "http://x.local", "permissions": ["admin"]}
    client.post("/api/apps/", json=payload, headers=ADMIN_HEADERS)
    r = client.post("/api/apps/", json=payload, headers=ADMIN_HEADERS)
    assert r.status_code == 409


def test_crear_app_rol_invalido_retorna_400(client):
    r = client.post("/api/apps/", json={
        "name": "MalaApp", "version": "1.0",
        "href": "http://x.local", "permissions": ["superadmin"]
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 400


# ── Listar apps ───────────────────────────────────────────────────────────────

def test_listar_apps_vacio(client):
    r = client.get("/api/apps/", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_listar_apps_con_paginacion(client):
    for i in range(5):
        client.post("/api/apps/", json={
            "name": f"App{i}", "version": "1.0",
            "href": f"http://app{i}.local", "permissions": ["empleado"]
        }, headers=ADMIN_HEADERS)

    r = client.get("/api/apps/?pagina=1&tamano=3", headers=ADMIN_HEADERS)
    body = r.json()
    assert body["total"] == 5
    assert len(body["apps"]) == 3
    assert body["paginas"] == 2


# ── mis-apps ──────────────────────────────────────────────────────────────────

def test_mis_apps_sin_departamento_retorna_vacio(client):
    r = client.get("/api/apps/mis-apps")
    assert r.status_code == 200
    assert r.json()["apps"] == []


def test_mis_apps_filtra_por_rol(client, db):
    # Crear app visible para jefe
    client.post("/api/apps/", json={
        "name": "App Gerencial", "version": "1.0",
        "href": "http://gerencial.local", "permissions": ["admin", "jefe"]
    }, headers=ADMIN_HEADERS)

    # Crear app visible solo para admin
    client.post("/api/apps/", json={
        "name": "App Admin", "version": "1.0",
        "href": "http://admin.local", "permissions": ["admin"]
    }, headers=ADMIN_HEADERS)

    # Asignar el usuario de prueba (U001) como jefe
    dep = Departamento(nombre="Test", descripcion=None,
                       servidor_id="local", empresa_cod="001")
    db.add(dep)
    db.flush()
    db.add(UsuarioDepartamento(
        cod_usuario=MOCK_PAYLOAD["sub"],
        servidor_id=MOCK_PAYLOAD["servidor_id"],
        departamento_id=dep.id,
        rol="jefe",
    ))
    db.commit()

    r = client.get("/api/apps/mis-apps")
    assert r.status_code == 200
    body = r.json()
    nombres = [a["name"] for a in body["apps"]]
    assert "App Gerencial" in nombres
    assert "App Admin" not in nombres


# ── Actualizar y eliminar ─────────────────────────────────────────────────────

def test_actualizar_app(client):
    client.post("/api/apps/", json={
        "name": "AppX", "version": "1.0",
        "href": "http://x.local", "permissions": ["empleado"]
    }, headers=ADMIN_HEADERS)

    r = client.put("/api/apps/AppX", json={"version": "2.0"}, headers=ADMIN_HEADERS)
    assert r.status_code == 200
    assert r.json()["app"]["version"] == "2.0"


def test_eliminar_app(client):
    client.post("/api/apps/", json={
        "name": "AppBorrar", "version": "1.0",
        "href": "http://borrar.local", "permissions": ["admin"]
    }, headers=ADMIN_HEADERS)

    r = client.delete("/api/apps/AppBorrar", headers=ADMIN_HEADERS)
    assert r.status_code == 200

    r2 = client.get("/api/apps/", headers=ADMIN_HEADERS)
    nombres = [a["name"] for a in r2.json()["apps"]]
    assert "AppBorrar" not in nombres


def test_actualizar_permisos_app(client):
    client.post("/api/apps/", json={
        "name": "AppPermisos", "version": "1.0",
        "href": "http://perm.local", "permissions": ["admin"]
    }, headers=ADMIN_HEADERS)

    r = client.post("/api/apps/AppPermisos/permisos",
                    json={"permissions": ["admin", "jefe", "empleado"]},
                    headers=ADMIN_HEADERS)
    assert r.status_code == 200
    assert set(r.json()["permissions"]) == {"admin", "jefe", "empleado"}
