from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
	informacion_cambio_pensum,
	seguimiento_auth,
	seguimiento_ies,
	seguimiento_convenios,
	seguimiento_catalogo,
	seguimiento_usuarios,
	seguimiento_actividades,
	seguimiento_informes,
	matricula_cero,
)

load_dotenv()

app = FastAPI(title="API")

# CORS: sin esto, el navegador bloquea las respuestas hacia el frontend
# React (portal_mc_fastapi) aunque el backend responda bien — el request
# aparece en el Network tab pero JS nunca ve la respuesta (lo que se ve
# como "usuario o contraseña inválidos" en el login, aunque en realidad
# nunca llegó a validar nada). Se usa "*" porque la auth es 100% por header
# Authorization: Bearer (no hay cookies de sesión de por medio), así que
# permitir cualquier origen no expone nada sensible.
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
	# Sin esto, el navegador bloquea la lectura de Content-Disposition desde
	# JS en requests cross-origin (solo expone un set "seguro" de headers por
	# defecto), y la descarga de informes en PDF cae siempre al nombre de
	# archivo genérico en vez del nombre real que arma el backend.
	expose_headers=["Content-Disposition"],
)

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
app.include_router(informacion_cambio_pensum.router, prefix="/api/informacion-cambio-pensum")

# ── Módulo Seguimiento Convenios MC ──────────────────────────────────────────
# OJO: estos routers ya definen su propio prefix completo en su propio
# APIRouter(prefix=...), así que NO se les pasa un prefix adicional aquí
# (a diferencia de usuarios.router / ies_preg_posg.router arriba, que sí
# reciben un prefix duplicado sobre el que ya traen — bug preexistente del
# repo, ver nota al final de este archivo).
app.include_router(seguimiento_auth.router)
app.include_router(seguimiento_ies.router)
app.include_router(seguimiento_convenios.router)
app.include_router(seguimiento_catalogo.router)
app.include_router(seguimiento_usuarios.router)
app.include_router(seguimiento_actividades.router)
app.include_router(seguimiento_informes.router)

# ── Matrícula Cero (Consulta + Tablero) ──────────────────────────────────────
# Nuevo, separado de /consulta (que se deja intacto). También define su
# propio prefix completo ("/matricula-cero"), sin prefix adicional aquí.
app.include_router(matricula_cero.router)



@app.get("/")
def healthz():
	return {"status": "ok", "time": time.time()}

# NOTA (revisión solicitada, no corregida automáticamente):
# usuarios.router e ies_preg_posg.router ya definen su propio prefix interno
# ("/usuarios" y "/ies-preg-posg" respectivamente) y AQUÍ se les vuelve a pasar
# el mismo prefix vía include_router(..., prefix=...). FastAPI concatena
# ambos, así que sus rutas reales quedan en /usuarios/usuarios/... y
# /ies-preg-posg/ies-preg-posg/... en vez de /usuarios/... e
# /ies-preg-posg/.... Lo dejamos tal cual porque no era parte del alcance
# pedido (agregar endpoints de Seguimiento), pero probablemente valga la pena
# corregirlo en el frontend/Postman que ya esté apuntando a esas rutas (si
# apunta a /usuarios/... solamente, hoy le está fallando).
