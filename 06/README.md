# Folder 06 - VinAgent Packaged by Lab12 Standard

Theo yeu cau bo sung, Lab05 va Lab06 la cung mot project chung: `vinagent`.

Folder nay dong goi lai project do theo checklist trien khai Lab12 tai:

- `06/vinagent`

## Thanh phan chinh trong package

- `Dockerfile` (multi-stage, production build cho Next.js)
- `docker-compose.yml` (chay local stack)
- `.env.example`
- `.dockerignore`
- `railway.toml`, `render.yaml`
- Health/ready endpoints:
  - `GET /api/health`
  - `GET /api/ready`
- Guard cho chat endpoint:
  - API key auth
  - rate limit
  - budget guard
- `check_production_ready.js`

## Cach chay nhanh

```bash
cd 06/vinagent
cp .env.example .env.local
docker compose up --build
npm run check:lab12
```
