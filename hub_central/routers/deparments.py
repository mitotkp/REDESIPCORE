import os
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
from dotenv import load_dotenv

from hub_central.classes.models import DepartamentoCreate, AsignarUsuario
from hub_central.database.database import get_db
from hub_central.database.models import Departamento, UsuarioDepartamento, ROLES_VALIDOS

load_dotenv()

api_key = os.getenv("SECRET_KEY")
algoritmo = os.getenv("ALGORITHM")
security_scheme = HTTPBearer()

router = APIRouter(prefix="/api/departamentos", tags=["Departamentos"])


def obtener_payload(credenciales: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credenciales.credentials
    try:
        return jwt.decode(token, api_key, algorithms=[algoritmo])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o corrupto.")


def verificar_admin(x_admin_key: str | None = Header(default=None)):
    admin_secret = os.getenv("ADMIN_SECRET")
    if not admin_secret or x_admin_key != admin_secret:
        raise HTTPException(
            status_code=403, detail="Acceso denegado. Se requiere clave de administrador."
        )


@router.get("/")
async def listar_departamentos(
    payload: dict = Depends(obtener_payload),
    db: Session = Depends(get_db),
):
    servidor_id = payload["servidor_id"]
    deps = (
        db.query(Departamento)
        .filter(Departamento.servidor_id == servidor_id)
        .all()
    )
    return {
        "status": "success",
        "departamentos": [
            {
                "id": d.id,
                "nombre": d.nombre,
                "descripcion": d.descripcion,
                "servidor_id": d.servidor_id,
                "empresa_cod": d.empresa_cod,
            }
            for d in deps
        ],
    }


@router.post("/")
async def crear_departamento(
    datos: DepartamentoCreate,
    payload: dict = Depends(obtener_payload),
    _: None = Depends(verificar_admin),
    db: Session = Depends(get_db),
):
    nuevo = Departamento(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        servidor_id=datos.servidor_id,
        empresa_cod=datos.empresa_cod,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {
        "status": "success",
        "departamento": {"id": nuevo.id, "nombre": nuevo.nombre},
    }


@router.delete("/{departamento_id}")
async def eliminar_departamento(
    departamento_id: int,
    payload: dict = Depends(obtener_payload),
    _: None = Depends(verificar_admin),
    db: Session = Depends(get_db),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")
    db.delete(dep)
    db.commit()
    return {"status": "success", "mensaje": f"Departamento '{dep.nombre}' eliminado."}


@router.post("/asignar-usuario")
async def asignar_usuario(
    datos: AsignarUsuario,
    payload: dict = Depends(obtener_payload),
    _: None = Depends(verificar_admin),
    db: Session = Depends(get_db),
):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Valores permitidos: {ROLES_VALIDOS}",
        )

    dep = db.query(Departamento).filter(Departamento.id == datos.departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")

    existente = (
        db.query(UsuarioDepartamento)
        .filter(
            UsuarioDepartamento.cod_usuario == datos.cod_usuario,
            UsuarioDepartamento.servidor_id == payload["servidor_id"],
            UsuarioDepartamento.departamento_id == datos.departamento_id,
        )
        .first()
    )

    if existente:
        existente.rol = datos.rol
        db.commit()
        return {"status": "success", "mensaje": "Rol actualizado correctamente."}

    asignacion = UsuarioDepartamento(
        cod_usuario=datos.cod_usuario,
        servidor_id=payload["servidor_id"],
        departamento_id=datos.departamento_id,
        rol=datos.rol,
    )
    db.add(asignacion)
    db.commit()
    return {"status": "success", "mensaje": "Usuario asignado al departamento correctamente."}


@router.delete("/usuarios/{asignacion_id}")
async def remover_usuario(
    asignacion_id: int,
    payload: dict = Depends(obtener_payload),
    _: None = Depends(verificar_admin),
    db: Session = Depends(get_db),
):
    asignacion = (
        db.query(UsuarioDepartamento)
        .filter(UsuarioDepartamento.id == asignacion_id)
        .first()
    )
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    db.delete(asignacion)
    db.commit()
    return {"status": "success", "mensaje": "Usuario removido del departamento."}


@router.get("/{departamento_id}/usuarios")
async def listar_usuarios_departamento(
    departamento_id: int,
    payload: dict = Depends(obtener_payload),
    _: None = Depends(verificar_admin),
    db: Session = Depends(get_db),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")

    usuarios = (
        db.query(UsuarioDepartamento)
        .filter(UsuarioDepartamento.departamento_id == departamento_id)
        .all()
    )
    return {
        "status": "success",
        "departamento": dep.nombre,
        "usuarios": [
            {"id": u.id, "cod_usuario": u.cod_usuario, "rol": u.rol}
            for u in usuarios
        ],
    }
