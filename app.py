from fastapi import FastAPI
from dotenv import load_dotenv

from api.routers import auth, consulta, informacion_personal, changelog, renovaciones_extemporaneas

load_dotenv()

app = FastAPI(title="API")

app.include_router(auth.router, prefix="/auth")
app.include_router(consulta.router, prefix="/consulta")
app.include_router(informacion_personal.router, prefix="/informacion_personal")
app.include_router(changelog.router, prefix="/changelog")
app.include_router(renovaciones_extemporaneas.router, prefix="/renovaciones-extemporaneas")


@app.get("/")
def healthz():
	return {"status": "ok"}