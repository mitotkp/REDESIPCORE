import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from hub_central.classes.models import AppCreate, AppUpdate, AppPermisos
from hub_central.database.database import get_db
from hub_central.database.models import UsuarioDepartamento, ROLES_VALIDOS
from hub_central.helpers.apps_helper import obtener_apps, guardar_apps, buscar_app
from hub_central.helpers.auth_deps import obtener_payload, verificar_admin
from hub_central.helpers.audit import auditar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/apps", tags=["Aplicaciones"])


@router.get("/mis-apps")
async def mis_apps(
    payload: dict = Depends(obtener_payload),
    db: Session   = Depends(get_db),
):
    cod_usuario = payload["sub"]
    servidor_id = payload["servidor_id"]

    roles_usuario = list({
        a.rol for a in db.query(UsuarioDepartamento).filter(
            UsuarioDepartamento.cod_usuario == cod_usuario,
            UsuarioDepartamento.servidor_id == servidor_id,
        ).all()
    })

    if not roles_usuario:
        return {"status": "success", "roles": [], "apps": []}

    apps_visibles = [
        app for app in obtener_apps()["apps"]
        if any(rol in app.get("permissions", []) for rol in roles_usuario)
    ]

    return {"status": "success", "roles": roles_usuario, "apps": apps_visibles}


@router.get("/")
async def listar_apps(
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    pagina: int   = Query(1,  ge=1),
    tamano: int   = Query(20, ge=1, le=100),
):
    todas = obtener_apps()["apps"]
    total = len(todas)
    skip  = (pagina - 1) * tamano
    page  = todas[skip: skip + tamano]

    return {
        "status":  "success",
        "total":   total,
        "pagina":  pagina,
        "tamano":  tamano,
        "paginas": (total + tamano - 1) // tamano if total else 0,
        "apps":    page,
    }


@router.post("/", status_code=201)
async def crear_app(
    datos: AppCreate,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    roles_invalidos = [r for r in datos.permissions if r not in ROLES_VALIDOS]
    if roles_invalidos:
        raise HTTPException(status_code=400,
                            detail=f"Roles inválidos: {roles_invalidos}. Permitidos: {ROLES_VALIDOS}")

    if buscar_app(datos.name)[0] is not None:
        raise HTTPException(status_code=409, detail=f"Ya existe una app llamada '{datos.name}'.")

    nueva = {"name": datos.name, "version": datos.version,
             "description": datos.description, "href": datos.href,
             "permissions": datos.permissions}

    data = obtener_apps()
    data["apps"].append(nueva)
    guardar_apps(data)

    auditar(db, payload, "APP_CREADA", f"name={datos.name} permisos={datos.permissions}")
    logger.info(f"App creada: '{datos.name}'")

    return {"status": "success", "app": nueva}


@router.put("/{nombre}")
async def actualizar_app(
    nombre: str,
    datos: AppUpdate,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    app, idx = buscar_app(nombre)
    if app is None:
        raise HTTPException(status_code=404, detail=f"App '{nombre}' no encontrada.")

    if datos.permissions is not None:
        invalidos = [r for r in datos.permissions if r not in ROLES_VALIDOS]
        if invalidos:
            raise HTTPException(status_code=400,
                                detail=f"Roles inválidos: {invalidos}. Permitidos: {ROLES_VALIDOS}")

    cambios = datos.model_dump(exclude_none=True)
    app.update(cambios)

    data = obtener_apps()
    data["apps"][idx] = app
    guardar_apps(data)

    auditar(db, payload, "APP_ACTUALIZADA", f"name={nombre} cambios={list(cambios.keys())}")
    logger.info(f"App actualizada: '{nombre}'")

    return {"status": "success", "app": app}


@router.delete("/{nombre}")
async def eliminar_app(
    nombre: str,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    app, idx = buscar_app(nombre)
    if app is None:
        raise HTTPException(status_code=404, detail=f"App '{nombre}' no encontrada.")

    data = obtener_apps()
    data["apps"].pop(idx)
    guardar_apps(data)

    auditar(db, payload, "APP_ELIMINADA", f"name={nombre}")
    logger.info(f"App eliminada: '{nombre}'")

    return {"status": "success", "mensaje": f"App '{nombre}' eliminada."}


@router.post("/{nombre}/permisos")
async def actualizar_permisos(
    nombre: str,
    datos: AppPermisos,
    payload: dict = Depends(obtener_payload),
    _: None       = Depends(verificar_admin),
    db: Session   = Depends(get_db),
):
    invalidos = [r for r in datos.permissions if r not in ROLES_VALIDOS]
    if invalidos:
        raise HTTPException(status_code=400,
                            detail=f"Roles inválidos: {invalidos}. Permitidos: {ROLES_VALIDOS}")

    app, idx = buscar_app(nombre)
    if app is None:
        raise HTTPException(status_code=404, detail=f"App '{nombre}' no encontrada.")

    app["permissions"] = datos.permissions
    data = obtener_apps()
    data["apps"][idx] = app
    guardar_apps(data)

    auditar(db, payload, "APP_PERMISOS_ACTUALIZADOS",
            f"name={nombre} roles={datos.permissions}")
    logger.info(f"Permisos de '{nombre}' actualizados: {datos.permissions}")

    return {"status": "success", "app": nombre, "permissions": datos.permissions}
