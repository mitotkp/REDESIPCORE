import logging
import os

logger = logging.getLogger(__name__)


def verificar_y_preparar_docker() -> None:
    """
    Verifica si Docker está disponible e intenta garantizar que el contenedor
    MySQL esté corriendo. En cualquier fallo solo registra un aviso — nunca
    detiene la aplicación.
    """
    try:
        import docker  # type: ignore
    except ImportError:
        logger.warning("SDK de Docker no instalado. Omitiendo verificación de contenedores.")
        return

    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        logger.warning(f"Docker no disponible en este entorno: {e}")
        return

    logger.info("Docker detectado. Verificando contenedor MySQL...")

    nombre    = os.getenv("MYSQL_CONTAINER_NAME", "redesipcore_mysql")
    puerto    = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_env = {
        "MYSQL_ROOT_PASSWORD": os.getenv("MYSQL_ROOT_PASS",  "root_redesipcore"),
        "MYSQL_DATABASE":      os.getenv("MYSQL_DB",         "redesipcore_hub"),
        "MYSQL_USER":          os.getenv("MYSQL_USER",       "hub_user"),
        "MYSQL_PASSWORD":      os.getenv("MYSQL_PASS",       "hub_pass"),
    }

    try:
        contenedor = client.containers.get(nombre)
        if contenedor.status != "running":
            logger.info(f"Contenedor '{nombre}' detenido — reiniciando...")
            contenedor.start()
            logger.info(f"Contenedor '{nombre}' iniciado correctamente.")
        else:
            logger.info(f"Contenedor '{nombre}' ya está en ejecución.")

    except docker.errors.NotFound:
        logger.info(f"Contenedor '{nombre}' no existe — creando...")
        try:
            client.containers.run(
                "mysql:8.0",
                name=nombre,
                environment=mysql_env,
                ports={"3306/tcp": puerto},
                detach=True,
                restart_policy={"Name": "unless-stopped"},
            )
            logger.info(f"Contenedor '{nombre}' creado y en ejecución.")
        except Exception as e:
            logger.error(f"No se pudo crear el contenedor MySQL: {e}")

    except Exception as e:
        logger.error(f"Error inesperado al gestionar contenedor Docker: {e}")
