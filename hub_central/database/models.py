from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from hub_central.database.database import Base

ROLES_VALIDOS = ["admin", "jefe", "empleado"]


class Departamento(Base):
    __tablename__ = "departamentos"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    nombre      = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
    servidor_id = Column(String(100), nullable=False)
    empresa_cod = Column(String(50),  nullable=False)


class UsuarioDepartamento(Base):
    __tablename__ = "usuarios_departamentos"
    __table_args__ = (
        UniqueConstraint("cod_usuario", "servidor_id", "departamento_id"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    cod_usuario     = Column(String(50),  nullable=False)
    servidor_id     = Column(String(100), nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id", ondelete="CASCADE"), nullable=False)
    rol             = Column(String(20),  nullable=False)  # admin | jefe | empleado
