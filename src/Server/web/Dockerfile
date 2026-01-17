# syntax=docker/dockerfile:1
FROM python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY web_requirements.txt /app/
RUN pip install --no-cache-dir -r web_requirements.txt

COPY ./src/Server/web/ .
COPY ./src/Server/Modules/ ./Modules/

# Make sure the init script is executable
RUN chmod +x /app/scripts/init_db.sh

EXPOSE 2000 2001 8000 8001 8080 11001

# Use the init script as entrypoint, which will then run the server
ENTRYPOINT ["/app/scripts/init_db.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
