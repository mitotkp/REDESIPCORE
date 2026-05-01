from fastapi import FastAPI
from hub_central.routers import auth, servidores, deparments
from hub_central.routers import apps as apps_router
from hub_central.database.database import Base, engine
import hub_central.database.models  # registra los modelos ORM con Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Core RedesIP",
    description="Portal Central Para Las Aplicaciones"
)

app.include_router(auth.router)
app.include_router(servidores.router)
app.include_router(deparments.router)
app.include_router(apps_router.router)


@app.get("/")
async def root():
    return {"mensaje": "El Hub Central esta en linea"}
