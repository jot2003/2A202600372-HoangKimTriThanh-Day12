# Deployment Information

## Public URL

https://vinagent-web-production.up.railway.app

## Platform

Railway

## Project Path

`06/vinagent`

## Test Commands

### Health Check
```bash
curl https://vinagent-web-production.up.railway.app/api/health
# Actual: 200 {"status":"ok","service":"vinagent-web",...}
```

### Readiness Check
```bash
curl https://vinagent-web-production.up.railway.app/api/ready
# Actual: 200 {"ready":true,...}
```

### Auth test (no key -> 401)
```bash
curl -X POST https://vinagent-web-production.up.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
# Actual: 401
```

### API test (with key -> 200)
```bash
curl -X POST https://vinagent-web-production.up.railway.app/api/chat \
  -H "X-API-Key: vinagent-lab12-key" \
  -H "X-User-Id: demo-user" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
# Actual: 200
```

### Rate limit test
```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://vinagent-web-production.up.railway.app/api/chat \
    -H "X-API-Key: vinagent-lab12-key" \
    -H "X-User-Id: rate-user" \
    -H "Content-Type: application/json" \
    -d '{"message":"rate test"}'
done
# Actual: request 11 -> 429
```

## Environment Variables Set

| Variable | Value |
|----------|-------|
| `NODE_ENV` | `production` |
| `AGENT_API_KEY` | set in Railway |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10` |
| `HOSTNAME` | `0.0.0.0` |

## Screenshots

- [Deployment dashboard](screenshots/dashboard_vinagent.png)
- [Service running](screenshots/running_vinagent.png)
- [Test results](screenshots/test_vinagent.png)

## Local Development

```bash
cd 06/vinagent
cp .env.example .env.local
docker compose up --build
```
