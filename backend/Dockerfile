FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the entire 'app' directory
COPY ./app ./app

EXPOSE 8080

# Use gunicorn with a single worker and an increased timeout.
# The timeout gives background tasks more time to complete if needed.
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080", "--timeout", "90"]

