FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# One worker on purpose: the live-queue WebSocket layer keeps its state in memory (see DEPLOYMENT.md).
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python -m uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 1"]
