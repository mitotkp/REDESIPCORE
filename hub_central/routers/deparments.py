import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from hub_central.classes.models import DepartamentoCreate, AsignarUsuario
from hub_central.database.database import get_db
from hub_central.database.models import Departamento, UsuarioDepartamento, ROLES_VALIDOS
from hub_central.helpers.auth_deps import obtener_payload, verificar_admin
from hub_central.helpers.audit import auditar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/departamentos", tags=["Departamentos"])


def _paginar(total: int, pagina: int, tamano: int) -> dict:
    return {
        "total":   total,
        "pagina":  pagina,
        "tamano":  tamano,
        "paginas": (total + tamano - 1) // tamano if total else 0,
    }


@router.get("/")
async def listar_departamentos(
    payload: dict    = Depends(obtener_payload),
    db: Session      = Depends(get_db),
    pagina: int      = Query(1,  ge=1),
    tamano: int      = Query(20, ge=1, le=100),
):
    servidor_id = payload["servidor_id"]
    skip  = (pagina - 1) * tamano
    q     = db.query(Departamento).filter(Departamento.servidor_id == servidor_id)
    total = q.count()
    deps  = q.offset(skip).limit(tamano).all()

    return {
        "status": "success",
        **_paginar(total, pagina, tamano),
        "departamentos": [
            {"id": d.id, "nombre": d.nombre, "descripcion": d.descripcion,
             "servidor_id": d.servidor_id, "empresa_cod": d.empresa_cod}
            for d in deps
        ],
    }


@router.post("/", status_code=201)
async def crear_departamento(
    datos: DepartamentoCreate,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    nuevo = Departamento(
        nombre=datos.nombre, descripcion=datos.descripcion,
        servidor_id=datos.servidor_id, empresa_cod=datos.empresa_cod,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    auditar(db, payload, "DEPARTAMENTO_CREADO", f"nombre={datos.nombre}")
    logger.info(f"Departamento creado: id={nuevo.id} nombre={nuevo.nombre}")

    return {"status": "success", "departamento": {"id": nuevo.id, "nombre": nuevo.nombre}}


@router.delete("/{departamento_id}")
async def eliminar_departamento(
    departamento_id: int,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")

    nombre = dep.nombre
    db.delete(dep)
    db.commit()

    auditar(db, payload, "DEPARTAMENTO_ELIMINADO", f"nombre={nombre}")
    logger.info(f"Departamento eliminado: id={departamento_id} nombre={nombre}")

    return {"status": "success", "mensaje": f"Departamento '{nombre}' eliminado."}


@router.post("/asignar-usuario")
async def asignar_usuario(
    datos: AsignarUsuario,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    if datos.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Permitidos: {ROLES_VALIDOS}")

    dep = db.query(Departamento).filter(Departamento.id == datos.departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")

    existente = db.query(UsuarioDepartamento).filter(
        UsuarioDepartamento.cod_usuario     == datos.cod_usuario,
        UsuarioDepartamento.servidor_id     == payload["servidor_id"],
        UsuarioDepartamento.departamento_id == datos.departamento_id,
    ).first()

    if existente:
        existente.rol = datos.rol
        db.commit()
        auditar(db, payload, "USUARIO_ROL_ACTUALIZADO",
                f"usuario={datos.cod_usuario} depto={dep.nombre} rol={datos.rol}")
        return {"status": "success", "mensaje": "Rol actualizado correctamente."}

    db.add(UsuarioDepartamento(
        cod_usuario=datos.cod_usuario,
        servidor_id=payload["servidor_id"],
        departamento_id=datos.departamento_id,
        rol=datos.rol,
    ))
    db.commit()

    auditar(db, payload, "USUARIO_ASIGNADO",
            f"usuario={datos.cod_usuario} depto={dep.nombre} rol={datos.rol}")
    logger.info(f"Usuario {datos.cod_usuario} asignado a '{dep.nombre}' como {datos.rol}")

    return {"status": "success", "mensaje": "Usuario asignado al departamento correctamente."}


@router.delete("/asignaciones/{asignacion_id}")
async def remover_usuario(
    asignacion_id: int,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    asignacion = db.query(UsuarioDepartamento).filter(
        UsuarioDepartamento.id == asignacion_id
    ).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")

    cod = asignacion.cod_usuario
    db.delete(asignacion)
    db.commit()

    auditar(db, payload, "USUARIO_REMOVIDO", f"usuario={cod}")
    logger.info(f"Usuario {cod} removido de departamento_id={asignacion.departamento_id}")

    return {"status": "success", "mensaje": "Usuario removido del departamento."}


@router.get("/{departamento_id}/usuarios")
async def listar_usuarios_departamento(
    departamento_id: int,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
    pagina: int   = Query(1,  ge=1),
    tamano: int   = Query(20, ge=1, le=100),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado.")

    skip     = (pagina - 1) * tamano
    q        = db.query(UsuarioDepartamento).filter(UsuarioDepartamento.departamento_id == departamento_id)
    total    = q.count()
    usuarios = q.offset(skip).limit(tamano).all()

    return {
        "status":       "success",
        "departamento": dep.nombre,
        **_paginar(total, pagina, tamano),
        "usuarios": [{"id": u.id, "cod_usuario": u.cod_usuario, "rol": u.rol} for u in usuarios],
    }
