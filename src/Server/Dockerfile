# syntax=docker/dockerfile:1
FROM python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/Server/ /app/

RUN chmod +x /app/server.py

EXPOSE 2000 2001 8000 8001 8080 11001

CMD ["python", "server.py"]
