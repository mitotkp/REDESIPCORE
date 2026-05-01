"""Tests de gestión de departamentos y asignación de roles."""
from tests.conftest import ADMIN_HEADERS


# ── Listar departamentos ───────────────────────────────────────────────────────

def test_listar_departamentos_vacio(client):
    r = client.get("/api/departamentos/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["total"] == 0
    assert body["departamentos"] == []


def test_listar_departamentos_paginacion_params(client):
    r = client.get("/api/departamentos/?pagina=1&tamano=5")
    assert r.status_code == 200
    assert "paginas" in r.json()


# ── Crear departamento ─────────────────────────────────────────────────────────

def test_crear_departamento_sin_admin_key_retorna_403(client):
    r = client.post("/api/departamentos/", json={
        "nombre": "TI", "servidor_id": "local", "empresa_cod": "001"
    })
    assert r.status_code == 403


def test_crear_departamento_con_admin_key(client):
    r = client.post("/api/departamentos/", json={
        "nombre": "Contabilidad", "descripcion": "Finanzas",
        "servidor_id": "local", "empresa_cod": "001"
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 201
    body = r.json()
    assert body["departamento"]["nombre"] == "Contabilidad"
    return body["departamento"]["id"]


# ── Asignar usuario ───────────────────────────────────────────────────────────

def test_asignar_usuario_rol_invalido(client):
    # Primero creamos un departamento
    r = client.post("/api/departamentos/", json={
        "nombre": "RRHH", "servidor_id": "local", "empresa_cod": "001"
    }, headers=ADMIN_HEADERS)
    dep_id = r.json()["departamento"]["id"]

    r2 = client.post("/api/departamentos/asignar-usuario", json={
        "cod_usuario": "U001", "departamento_id": dep_id, "rol": "dios"
    }, headers=ADMIN_HEADERS)
    assert r2.status_code == 400


def test_asignar_usuario_departamento_inexistente(client):
    r = client.post("/api/departamentos/asignar-usuario", json={
        "cod_usuario": "U001", "departamento_id": 99999, "rol": "empleado"
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 404


# ── Flujo completo ────────────────────────────────────────────────────────────

def test_flujo_completo_departamento(client):
    # 1. Crear
    r = client.post("/api/departamentos/", json={
        "nombre": "Ventas", "servidor_id": "local", "empresa_cod": "001"
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 201
    dep_id = r.json()["departamento"]["id"]

    # 2. Asignar usuario
    r = client.post("/api/departamentos/asignar-usuario", json={
        "cod_usuario": "U002", "departamento_id": dep_id, "rol": "jefe"
    }, headers=ADMIN_HEADERS)
    assert r.status_code == 200

    # 3. Listar usuarios
    r = client.get(f"/api/departamentos/{dep_id}/usuarios", headers=ADMIN_HEADERS)
    assert r.status_code == 200
    usuarios = r.json()["usuarios"]
    assert len(usuarios) == 1
    asig_id = usuarios[0]["id"]
    assert usuarios[0]["rol"] == "jefe"

    # 4. Remover usuario
    r = client.delete(f"/api/departamentos/asignaciones/{asig_id}", headers=ADMIN_HEADERS)
    assert r.status_code == 200

    # 5. Eliminar departamento
    r = client.delete(f"/api/departamentos/{dep_id}", headers=ADMIN_HEADERS)
    assert r.status_code == 200


def test_eliminar_departamento_inexistente(client):
    r = client.delete("/api/departamentos/99999", headers=ADMIN_HEADERS)
    assert r.status_code == 404
