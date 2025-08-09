from fastapi import FastAPI
from dotenv import load_dotenv

from app.core.config import APP_TITLE
from app.routers import auth, consulta, informacion_personal

load_dotenv()

app = FastAPI(title=APP_TITLE)

app.include_router(auth.router, prefix="/auth")
app.include_router(consulta.router, prefix="/consulta")
app.include_router(informacion_personal.router, prefix="/informacion_personal")