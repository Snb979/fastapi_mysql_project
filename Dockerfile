FROM python:3.10

# Instala dependencias del sistema necesarias para cryptography
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

WORKDIR /app

COPY app/requirements.txt .
COPY app/.env .env

RUN pip install -r requirements.txt

COPY app/ .


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
