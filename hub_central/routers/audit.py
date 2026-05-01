from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from hub_central.database.database import get_db
from hub_central.database.models import Auditoria
from hub_central.helpers.auth_deps import obtener_payload, verificar_admin

router = APIRouter(prefix="/api/audit", tags=["Auditoría"])


@router.get("/")
async def listar_auditoria(
    payload: dict       = Depends(obtener_payload),
    _: None             = Depends(verificar_admin),
    db: Session         = Depends(get_db),
    pagina: int         = Query(1,    ge=1),
    tamano: int         = Query(50,   ge=1, le=200),
    cod_usuario: str | None = Query(None, description="Filtrar por código de usuario"),
    accion: str | None      = Query(None, description="Filtrar por tipo de acción"),
):
    q = db.query(Auditoria).filter(Auditoria.servidor_id == payload["servidor_id"])

    if cod_usuario:
        q = q.filter(Auditoria.cod_usuario == cod_usuario)
    if accion:
        q = q.filter(Auditoria.accion == accion)

    total    = q.count()
    skip     = (pagina - 1) * tamano
    registros = q.order_by(Auditoria.timestamp.desc()).offset(skip).limit(tamano).all()

    return {
        "status":  "success",
        "total":   total,
        "pagina":  pagina,
        "tamano":  tamano,
        "paginas": (total + tamano - 1) // tamano if total else 0,
        "registros": [
            {
                "id":          r.id,
                "timestamp":   r.timestamp.isoformat(),
                "cod_usuario": r.cod_usuario,
                "accion":      r.accion,
                "detalle":     r.detalle,
            }
            for r in registros
        ],
    }
