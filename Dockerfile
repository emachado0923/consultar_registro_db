FROM python:3.9-slim

WORKDIR /app

# Instala dependencias primero para aprovechar la cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la app
COPY . .

# Build Reflex en modo producción
RUN reflex export --frontend-only

# Expone el puerto por defecto de Reflex (3000)
EXPOSE 3000

# Comando de arranque en producción
CMD ["reflex", "run", "--env", "prod"]