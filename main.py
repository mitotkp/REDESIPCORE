import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from hub_central.helpers.logging_config import configurar_logging

configurar_logging()
logger = logging.getLogger(__name__)

TESTING = os.getenv("TESTING", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not TESTING:
        from hub_central.database.database import inicializar_db
        from hub_central.helpers.docker_check import verificar_y_preparar_docker

        logger.info("Iniciando REDESIPCORE...")
        verificar_y_preparar_docker()
        inicializar_db()
        logger.info("Hub en línea.")
    yield


from hub_central.routers import auth, servidores, deparments, audit
from hub_central.routers import apps as apps_router

app = FastAPI(
    title="Core RedesIP",
    description="Portal Central Para Las Aplicaciones",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(servidores.router)
app.include_router(deparments.router)
app.include_router(apps_router.router)
app.include_router(audit.router)


@app.get("/", tags=["Estado"])
async def root():
    return {"mensaje": "El Hub Central está en línea", "version": "1.0.0"}
