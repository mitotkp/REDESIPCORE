import urllib.parse

_MSSQL  = {"mssql", "sqlserver", "sql server", "sql_server"}
_PG     = {"postgresql", "postgres"}
_MYSQL  = {"mysql", "mariadb"}


def construir_url_conexion(
    tipo: str,
    host: str,
    puerto: int | str,
    db_name: str,
    usuario: str,
    password: str,
    driver: str | None = None,
) -> str:
    """
    Genera la URL de conexión SQLAlchemy correcta según el tipo de BD.

    Tipos soportados:
      - MSSQL   : mssql, sqlserver, sql server, sql_server
      - Postgres : postgresql, postgres
      - MySQL   : mysql, mariadb
      - Otros   : se usa el tipo tal cual (fallback genérico)
    """
    tipo_norm = tipo.lower().strip()
    pwd = urllib.parse.quote_plus(password)

    if tipo_norm in _MSSQL:
        drv = (driver or "SQL Server").replace(" ", "+")
        return (
            f"mssql+pyodbc://{usuario}:{pwd}@{host}:{puerto}/{db_name}"
            f"?driver={drv}&TrustServerCertificate=yes"
        )

    if tipo_norm in _PG:
        return f"postgresql+psycopg2://{usuario}:{pwd}@{host}:{puerto}/{db_name}"

    if tipo_norm in _MYSQL:
        return f"mysql+pymysql://{usuario}:{pwd}@{host}:{puerto}/{db_name}"

    # Fallback: respeta el tipo que envió el usuario
    url = f"{tipo_norm}://{usuario}:{pwd}@{host}:{puerto}/{db_name}"
    if driver:
        url += f"?driver={driver.replace(' ', '+')}"
    return url


def construir_url_desde_config(config: dict, db_name: str | None = None) -> str:
    """Construye la URL a partir de un bloque de connections.json."""
    return construir_url_conexion(
        tipo=config["tipo"],
        host=config["host"],
        puerto=config["puerto"],
        db_name=db_name or config.get("db_name", "GENERAL"),
        usuario=config["hub_user"],
        password=config["hub_pass"],
        driver=config.get("driver"),
    )
