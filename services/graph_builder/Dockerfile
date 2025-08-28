FROM python:3.11-slim

WORKDIR /app

COPY services/graph_builder/requirements.txt requirements.txt
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt && \
    python -m spacy download pt_core_news_lg

COPY ./services/graph_builder/main.py /app/services/graph_builder/main.py
COPY ./services/common/ /app/services/common/
COPY ./config/ /app/config/
COPY ./assistant/ /app/assistant/
RUN touch services/__init__.py
RUN touch services/graph_builder/__init__.py

ENV PYTHONPATH=/app

CMD ["python", "-m", "services.graph_builder.main"]
