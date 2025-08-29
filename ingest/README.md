# KB Ingestion → Qdrant

This container embeds files from `/kb` and writes vectors + metadata to Qdrant.

## Supported formats
- `.md`, `.txt`
- `.pdf` (text extraction via `pypdf`)

## Usage (with Compose network)
```bash
# Build the ingestion image
docker compose -f docker-compose.yml -f compose.ingest.yml build ingest

# Run ingestion (reads ./kb on host)
docker compose -f docker-compose.yml -f compose.ingest.yml run --rm ingest   --kb-dir /kb --collection kb --recreate
```
