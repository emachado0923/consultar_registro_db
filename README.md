# API de Consulta de Registro Estudiantil

Este proyecto es una API RESTful construida con FastAPI para gestionar y consultar registros estudiantiles y académicos. Proporciona una interfaz segura y robusta para interactuar con la base de datos de información estudiantil.

## ✨ Características Principales

*   **Autenticación Segura:** Utiliza JWT para proteger los endpoints.
*   **Gestión de Estudiantes:** Operaciones CRUD para la información personal y académica de los estudiantes.
*   **Consultas Avanzadas:** Endpoints específicos para consultas complejas como deudores, renovaciones, y más.
*   **Registro de Cambios:** Mantiene un historial de cambios (changelog) para auditorías.
*   **Modularidad:** Código organizado en routers para una mejor mantenibilidad y escalabilidad.
*   **Documentación Automática:** Gracias a FastAPI, se genera documentación interactiva de la API (Swagger UI y ReDoc).

## Endpoints de la API

A continuación se muestra una tabla con los principales grupos de endpoints disponibles:

| Prefijo del Endpoint                      | Descripción                                                                      |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| `/auth`                                   | Autenticación y generación de tokens JWT.                                        |
| `/consulta`                               | Consultas generales sobre los registros.                                         |
| `/informacion_personal`                   | Gestión de la información personal de los estudiantes.                           |
| `/changelog`                              | Historial de cambios realizados en los registros.                                |
| `/renovaciones-extemporaneas`             | Gestión de renovaciones extemporáneas.                                          |
| `/informacion-programas-academicos`       | Información sobre los programas académicos.                                      |
| `/renuncia-o-terminacion`                 | Gestión de renuncias o terminaciones de modalidad.                               |
| `/suspension-especial`                    | Gestión de suspensiones especiales.                                              |
| `/estudiante-obtiene-grado`               | Registro de la obtención de grado por parte de los estudiantes.                  |
| `/prorroga-periodo-de-gracia`             | Gestión de prórrogas del período de gracia.                                      |
| `/renuncia-modalidad`                     | Gestión de renuncias a la modalidad de estudio.                                  |
| `/informacion-deudores`                   | Consulta de información sobre deudores.                                          |

Para ver la documentación detallada y probar los endpoints, visita `/docs` o `/redoc` en la URL base de la aplicación una vez que esté en ejecución.

## 🚀 Cómo Empezar

Sigue estos pasos para configurar el entorno de desarrollo local.

### Prerrequisitos

*   Python 3.9+
*   Docker (opcional, para despliegue)
*   Un gestor de paquetes de Python como `pip`

### Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/emachado0923/consultar_registro_db.git
    cd consultar_registro_db
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    python -m venv venv
    # En Windows
    .\venv\Scripts\activate
    # En macOS/Linux
    source venv/bin/activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura las variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto y añade las siguientes variables. Reemplaza los valores con tu configuración.
    ```env
    DATABASE_URL="postgresql://user:password@host:port/database"
    SECRET_KEY="tu_super_secreto_aqui"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ```

## Uso

### Ejecutando la Aplicación

Para iniciar la aplicación en modo de desarrollo con recarga automática:

```bash
uvicorn app:app --reload
```

La API estará disponible en `http://127.0.0.1:8000`.

### Usando Docker

También puedes construir y ejecutar la aplicación usando Docker.

1.  **Construye la imagen de Docker:**
    ```bash
    docker build -t consultar-registro-api .
    ```

2.  **Ejecuta el contenedor:**
    ```bash
    docker run -d -p 8000:8000 --env-file .env --name consultar-registro-container consultar-registro-api
    ```

## 🛠️ Tecnologías Utilizadas

*   **Backend:**
    *   [FastAPI](https://fastapi.tiangolo.com/): Framework web de alto rendimiento para construir APIs.
    *   [Pydantic](https://pydantic-docs.helpmanual.io/): Para la validación de datos.
    *   [SQLAlchemy](https://www.sqlalchemy.org/): ORM para la interacción con la base de datos.
    *   [python-dotenv](https://github.com/theskumar/python-dotenv): Para la gestión de variables de entorno.
    *   [passlib](https://passlib.readthedocs.io/en/stable/): Para el hashing de contraseñas.
    *   [python-jose](https://github.com/mpdavis/python-jose): Para la implementación de JWT.

*   **Base de Datos:**
    *   PostgreSQL (o la base de datos que configures en `DATABASE_URL`).

*   **Despliegue:**
    *   [Docker](https://www.docker.com/): Para la contenerización.
    *   [Gunicorn](https://gunicorn.org/): Servidor WSGI para producción.
    *   [Cloud Build](https://cloud.google.com/build): Para la automatización de builds en Google Cloud.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Si deseas contribuir, por favor sigue estos pasos:

1.  Haz un fork del proyecto.
2.  Crea una nueva rama (`git checkout -b feature/nueva-caracteristica`).
3.  Realiza tus cambios y haz commit (`git commit -m 'Añade nueva característica'`).
4.  Haz push a la rama (`git push origin feature/nueva-caracteristica`).
5.  Abre un Pull Request.

Por favor, asegúrate de que tu código sigue las guías de estilo del proyecto y que los tests (si los hay) pasan.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
(Nota: No tienes un archivo LICENSE, pero es una buena práctica añadir uno).