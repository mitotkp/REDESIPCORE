from pydantic import BaseModel


# ── Servidores ────────────────────────────────────────────────────────────────

class ServidorRegistro(BaseModel):
    servidor: str
    host:     str
    puerto:   int
    db_name:  str | None = None
    tipo:     str
    driver:   str | None = None
    usuario:  str
    password: str


class CredencialesLogin(BaseModel):
    servidor: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ── Departamentos ─────────────────────────────────────────────────────────────

class DepartamentoCreate(BaseModel):
    nombre:      str
    descripcion: str | None = None
    servidor_id: str
    empresa_cod: str


class AsignarUsuario(BaseModel):
    cod_usuario:     str
    departamento_id: int
    rol:             str  # admin | jefe | empleado


# ── Aplicaciones (apps.json) ──────────────────────────────────────────────────

class AppCreate(BaseModel):
    name:        str
    version:     str
    description: str | None = None
    href:        str
    permissions: list[str]


class AppUpdate(BaseModel):
    version:     str | None = None
    description: str | None = None
    href:        str | None = None
    permissions: list[str] | None = None


class AppPermisos(BaseModel):
    permissions: list[str]
