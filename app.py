from fastapi import FastAPI
from dotenv import load_dotenv
import time

from api.routers import (
	auth,
	consulta,
	usuarios,
	informacion_personal,
	changelog,
	renovaciones_extemporaneas,
	informacion_programas_academicos,
	renuncia_o_terminacion,
	suspension_especial,
	estudiante_obtiene_grado,
	prorroga_periodo_de_gracia,
	renuncia_modalidad,
	informacion_deudores,
	suspension_temporal,
	renuncia_giros,
	ies_preg_posg,
	programas_preg_posg,
	reintegros,
	vw_giros_general_historico_ies,
)

load_dotenv()

app = FastAPI(title="API")

app.include_router(auth.router, prefix="/auth")
app.include_router(consulta.router, prefix="/consulta")
app.include_router(usuarios.router, prefix="/usuarios")
app.include_router(informacion_personal.router, prefix="/informacion_personal")
app.include_router(changelog.router, prefix="/changelog")
app.include_router(renovaciones_extemporaneas.router, prefix="/renovaciones-extemporaneas")
app.include_router(informacion_programas_academicos.router, prefix="/informacion-programas-academicos",)
app.include_router(renuncia_o_terminacion.router, prefix="/renuncia-o-terminacion")
app.include_router(suspension_especial.router, prefix="/suspension-especial")
app.include_router(estudiante_obtiene_grado.router, prefix="/estudiante-obtiene-grado")
app.include_router(prorroga_periodo_de_gracia.router, prefix="/prorroga-periodo-de-gracia")
app.include_router(renuncia_modalidad.router, prefix="/renuncia-modalidad")
app.include_router(informacion_deudores.router, prefix="/informacion-deudores")
app.include_router(suspension_temporal.router, prefix="/suspension-temporal")
app.include_router(renuncia_giros.router, prefix="/renuncia-giros")
app.include_router(ies_preg_posg.router, prefix="/ies-preg-posg")
app.include_router(programas_preg_posg.router, prefix="/programas-preg-posg")
app.include_router(reintegros.router, prefix="/reintegros")
app.include_router(vw_giros_general_historico_ies.router, prefix="/vw-giros-general")


@app.get("/")
def healthz():
	return {"status": "ok", "time": time.time()}