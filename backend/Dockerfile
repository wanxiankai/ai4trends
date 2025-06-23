# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy all application code
COPY ./app ./app

# Expose the port Cloud Run provides
EXPOSE 8080

# Use gunicorn to run the app with a SINGLE worker
# This is crucial for in-memory schedulers like the default APScheduler
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080"]
