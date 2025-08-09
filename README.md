# 🔍 Consulta de Registros en Base de Datos MySQL - FastAPI

API REST con FastAPI para autenticar usuarios y consultar registros por documento desde MySQL. Diseñada para ejecutarse en Cloud Run.

## Endpoints

- GET /healthz: healthcheck.
- POST /auth/login: body { username, password } → devuelve JWT.
- POST /auth/change-password: body { current_password, new_password } (Bearer).
- POST /auth/register: body { username, full_name, password } (Bearer admin).
- GET /consulta?documento=XXXXXXXX (Bearer): consulta en vista vw_matricula_cero_2025_2.

## Variables de entorno requeridas

Debe suministrarlas en Cloud Run (o localmente):

- LOGIN_DB_HOST, LOGIN_DB_USER, LOGIN_DB_PASSWORD, LOGIN_DB_DATABASE, LOGIN_DB_PORT (opcional)
- APP_DB_HOST, APP_DB_USER, APP_DB_PASSWORD, APP_DB_DATABASE, APP_DB_PORT (opcional)
- JWT_SECRET (se recomienda cambiarlo en producción)

## Desarrollo local

1) Instalar dependencias
```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Exportar variables de entorno (PowerShell)
```pwsh
$env:LOGIN_DB_HOST="localhost"
$env:LOGIN_DB_USER="user"
$env:LOGIN_DB_PASSWORD="pass"
$env:LOGIN_DB_DATABASE="analitica_fondos"
$env:APP_DB_HOST="localhost"
$env:APP_DB_USER="user"
$env:APP_DB_PASSWORD="pass"
$env:APP_DB_DATABASE="REDACTED"
$env:JWT_SECRET="change-me"
```

3) Levantar servidor
```pwsh
uvicorn app:app --reload --port 8080
```

## Despliegue en Cloud Run

Este repo incluye:

- Dockerfile: ejecuta uvicorn y respeta PORT.
- cloudbuild.yaml: build/push a Artifact Registry y deploy a Cloud Run.

Parámetros usados por Cloud Build (substitutions):

- _REPOSITORY_NAME
- _IMAGE_NAME
- _SERVICE_NAME
- _PORT (usar 8080)

Asegura definir variables de entorno en el servicio Cloud Run (UI o gcloud) para las credenciales de DB y JWT_SECRET.

## Notas de seguridad

- No publiques credenciales en el código ni en el repo.
- Use JWT_SECRET robusto y rota contraseñas.