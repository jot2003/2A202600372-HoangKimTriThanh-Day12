# VinAgent - Lab12 Packaging (from Lab05 + Lab06)

Day la ban dong goi project chung VinAgent (xay dung trong Lab05 + Lab06) theo checklist trien khai cua Lab12.

## Muc tieu Lab12 da dong goi

- Dockerfile multi-stage cho production
- docker-compose de chay local
- `.env.example` cho cau hinh environment
- API health/readiness:
  - `GET /api/health`
  - `GET /api/ready`
- API guard cho chat endpoint:
  - API key auth qua header `X-API-Key`
  - rate limiting (10 req/min/user, in-memory guard)
  - cost guard ($10/month/user, in-memory guard)
- Structured logging o `/api/chat`
- File deploy cloud:
  - `railway.toml`
  - `render.yaml`

## Chay local bang Docker

```bash
cp .env.example .env.local
docker compose up --build
```

Truy cap:

- App: `http://localhost:3000`
- Health: `http://localhost:3000/api/health`
- Ready: `http://localhost:3000/api/ready`

## Dang nhap va su dung

1. Mo `http://localhost:3000/dang-nhap`
2. Dang nhap bang tai khoan demo:
   - MSSV: `2022600001` / Mat khau: `1`
   - MSSV: `2022600002` / Mat khau: `1`
3. Vao trang chat/tao ke hoach de gui yeu cau cho agent.
4. Neu goi API truc tiep, nho them:
   - `X-API-Key: <AGENT_API_KEY>`
   - `X-User-Id: <your-user-id>`

Luu y:
- Khong co `X-API-Key` se bi tu choi (`401`).
- Qua gioi han 10 request/phut/user se bi `429`.

## Test nhanh API

```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/ready
```

Chat API (can key):

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "X-API-Key: dev-key-change-me" \
  -H "X-User-Id: test-user" \
  -H "Content-Type: application/json" \
  -d '{"message":"xin chao"}'
```

## Deploy

### Railway

```bash
railway init
railway up
railway domain
```

Set vars:

- `AGENT_API_KEY`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10`
- `GOOGLE_API_KEY` / `OPENAI_API_KEY` (neu dung provider that)

### Render

Su dung `render.yaml`, sau do set secret vars trong dashboard.
