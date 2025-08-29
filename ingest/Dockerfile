FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir qdrant-client sentence-transformers pypdf tqdm
COPY ingest_kb.py /app/ingest_kb.py
ENTRYPOINT ["python", "/app/ingest_kb.py"]
