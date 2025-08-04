FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Build the Reflex app
RUN python -m reflex init

# Generate production build
RUN python -m reflex build --frontend-only

# Expose the port Reflex runs on
EXPOSE 8000

# Start the Reflex application in production mode
ENTRYPOINT ["python", "-m", "reflex", "run", "--env", "prod"]
