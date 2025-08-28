# jarvis_mark2/services/llm.Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY services/llm_requirements.txt requirements.txt
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copia seletivamente apenas o código necessário
COPY ./services/llm_service.py /app/services/llm_service.py
COPY ./services/common/ /app/services/common/
COPY ./config/ /app/config/
COPY ./database/ /app/database/
RUN touch services/__init__.py

ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "services.llm_service:app", "--host", "0.0.0.0", "--port", "8002"]
