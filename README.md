# HN Support Stack (Self-Hosted)

All-in-house customer support + project tracking + local LLM:

- **Zammad** (help desk) + Postgres + Elasticsearch
- **OpenProject** (Jira-class issues/PM) + Postgres + Memcached
- **vLLM** (OpenAI-compatible local LLM server)
- **Qdrant** (vector DB for RAG)
- **FastAPI Bridge** exposing `/ticket.create`, `/issue.create`, `/chat` (no egress)

## Prereqs
- Docker Engine + Docker Compose v2
- Host sysctl for Elasticsearch:
  ```bash
  sudo sysctl -w vm.max_map_count=262144
  ```

## Quick start
```bash
cp .env.example .env
# edit the tokens/passwords in .env

docker compose up -d
docker compose ps
curl http://127.0.0.1:8787/health
```

### Default endpoints (loopback)
- Zammad → http://127.0.0.1:8081
- OpenProject → http://127.0.0.1:8082
- vLLM (OpenAI-compatible) → http://127.0.0.1:8000/v1
- Bridge → http://127.0.0.1:8787

## Initial setup
1. **Zammad**: Create admin user in the UI → generate an API token (`Profile → Access Tokens`), paste into `.env` as `ZAMMAD_TOKEN`.
2. **OpenProject**: Complete the setup wizard → `My account → Access tokens → API` → copy token to `.env` as `OPENPROJECT_API_KEY`.

## Using the bridge
Create a ticket:
```bash
curl -X POST http://127.0.0.1:8787/ticket.create \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Customer cannot login",
    "body":"User reports 2FA loop, email alice@example.com",
    "customer_email":"alice@example.com",
    "group":"Users"
  }'
```

Create an issue:
```bash
curl -X POST http://127.0.0.1:8787/issue.create \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": 1,
    "subject": "Login page error",
    "description": "2FA loop when browser has blocked cookies",
    "type_id": 1
  }'
```

Local chat completion (passes through to vLLM):
```bash
curl -X POST http://127.0.0.1:8787/chat \  -H 'Content-Type: application/json' \  -d '{
    "model":"local-cs",
    "messages":[{"role":"user","content":"Hello"}],
    "temperature":0
  }'
```

## Repo layout
```
.
├─ docker-compose.yml
├─ .env.example
├─ bridge/
│  ├─ app.py
│  └─ Dockerfile
├─ .github/workflows/
│  ├─ ci.yml
│  └─ release.yml
├─ .gitignore
├─ LICENSE
└─ Makefile
```

## GitHub setup (quick)
```bash
git init
git add -A
git commit -m "init: hn-support stack"
# if you use GitHub CLI:
gh repo create hewesnguyen/hn-support --private --source=. --remote=origin --push
# otherwise, create the repo on GitHub and:
git remote add origin git@github.com:<org-or-user>/hn-support.git
git push -u origin main
```

## CI/CD
- **CI (`ci.yml`)**: validates Compose, compiles `bridge/app.py`, and builds the bridge image.
- **Release (`release.yml`)**: on tags `v*.*.*`, builds and pushes `ghcr.io/<owner>/hn-support-bridge`.
You can pull from GHCR to other hosts that run the stack.

## Notes
- Everything binds to `127.0.0.1` by default (local-only). Expose to LAN by adjusting `ports:`.
- For GPUs, uncomment the `deploy.resources.reservations.devices` block on the `llm` service and ensure NVIDIA Container Toolkit is installed.
- Use a real model path in `LLM_MODELS_DIR` and `LLM_MODEL`. The default assumes a local, already-downloaded model folder.


## Optional: GPU enable for vLLM
GPU boxes: add the GPU override file.
```bash
docker compose -f docker-compose.yml -f compose.gpu.yml up -d
```
(Requires NVIDIA Container Toolkit; this sets `--gpus all` and nudges vLLM to use CUDA.)

## Optional: TLS reverse proxy for LAN
Generate a wildcard cert and expose everything at `*.hn.local`:
```bash
# generate certs (mkcert preferred; falls back to openssl self-signed)
bash scripts/gen-certs.sh hn.local

# bring up with proxy
docker compose -f docker-compose.yml -f compose.proxy.yml up -d
```

Add host entries on your client:
```
<HOST_IP> zammad.hn.local openproject.hn.local qdrant.hn.local llm.hn.local bridge.hn.local
```
Now open:
- https://zammad.hn.local
- https://openproject.hn.local
- https://qdrant.hn.local
- https://llm.hn.local
- https://bridge.hn.local

> With `mkcert`, you can add the generated CA to your OS trust store so browsers accept the cert without warnings.

## Ingest your KB into Qdrant
Place Markdown/TXT/PDFs under `./kb/` and run the ingestion container:
```bash
docker compose -f docker-compose.yml -f compose.ingest.yml build ingest
docker compose -f docker-compose.yml -f compose.ingest.yml run --rm ingest \
  --kb-dir /kb --collection kb --recreate
```
Change the embedding model by setting `EMBED_MODEL` in your environment or `.env`. Default: `sentence-transformers/all-MiniLM-L6-v2`.
