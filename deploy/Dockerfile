FROM python:3.12-slim

WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart \
    anthropic python-dotenv websockets httpx pydantic twilio

COPY app ./app
COPY prompts ./prompts

ENV LEADS_DB_PATH=/data/leads.db
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
