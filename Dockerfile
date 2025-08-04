FROM python:3.9-slim

WORKDIR /app

# Copy application files
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Build the Reflex app
RUN reflex init
RUN reflex export --no-frontend

# Expose the port Reflex runs on
EXPOSE 8000

# Start the Reflex application
CMD ["reflex", "run", "--env", "prod", "--backend-only"]
