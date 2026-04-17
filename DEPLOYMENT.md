# Deployment Information

## Public URL

https://agent-api-production-dae1.up.railway.app

## Platform

Railway

## How to Deploy

### Option A: Railway (< 5 phút)

```bash
# 1. Cài Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Init project (chạy trong thư mục 06-lab-complete/)
cd 06-lab-complete
railway init

# 4. Thêm Redis add-on trên Railway Dashboard
#    → Project → Add Service → Redis

# 5. Set environment variables
railway variables set AGENT_API_KEY=<your-secret-key>
railway variables set ENVIRONMENT=production
railway variables set JWT_SECRET=<your-jwt-secret>
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
# REDIS_URL sẽ tự inject từ Redis add-on

# 6. Deploy
railway up

# 7. Lấy domain
railway domain
```

### Option B: Render

1. Push code lên GitHub
2. Vào [render.com](https://render.com) → Sign up
3. New → Blueprint → Connect GitHub repo
4. Render tự đọc `render.yaml`
5. Set `AGENT_API_KEY` và `JWT_SECRET` trong Dashboard > Environment
6. Deploy!

---

## Test Commands

### Health Check
```bash
curl https://agent-api-production-dae1.up.railway.app/health
# Actual: 200 {"status":"ok","version":"1.0.0","environment":"production",...}
```

### Readiness Check
```bash
curl https://agent-api-production-dae1.up.railway.app/ready
# Actual: 200 {"ready":true,"redis":"ok"}
```

### API Test (with authentication)
```bash
curl -X POST https://agent-api-production-dae1.up.railway.app/ask \
  -H "X-API-Key: lab-day12-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello, what is Docker?"}'
# Actual: 200 with JSON answer payload
```

### Auth test (no key → 401)
```bash
curl -X POST https://agent-api-production-dae1.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
# Actual: 401 Unauthorized
```

### Rate limit test
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://agent-api-production-dae1.up.railway.app/ask \
    -H "X-API-Key: lab-day12-key-2026" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test","question":"test"}'
done
# Actual: first 10 -> 200, request 11 -> 429
```

## Environment Variables Set

| Variable | Description |
|----------|-------------|
| `PORT` | `8000` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` (service reference) |
| `AGENT_API_KEY` | `lab-day12-key-2026` |
| `JWT_SECRET` | `lab-day12-jwt-secret` |
| `ENVIRONMENT` | `production` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |

## Local Development

```bash
cd 06-lab-complete
cp .env.example .env.local
# Edit .env.local with your values
docker compose up
# Test: curl http://localhost:8000/health
```

---

_Đã cập nhật bằng kết quả deploy thực tế trên Railway._
