FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN useradd --create-home bank && mkdir -p /app/data && chown bank /app/data
USER bank

EXPOSE 8000
CMD ["sh", "-c", "python -m scripts.seed --if-empty && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
