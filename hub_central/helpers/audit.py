import logging
from sqlalchemy.orm import Session
from hub_central.database.models import Auditoria

logger = logging.getLogger(__name__)


def auditar(
    db: Session,
    payload: dict,
    accion: str,
    detalle: str | None = None,
) -> None:
    """Registra una acción en la tabla de auditoría. No lanza excepciones."""
    try:
        db.add(Auditoria(
            cod_usuario=payload["sub"],
            servidor_id=payload["servidor_id"],
            accion=accion,
            detalle=detalle,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"Error al registrar auditoría [{accion}]: {e}")
        db.rollback()
