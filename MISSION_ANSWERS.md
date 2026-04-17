# Day 12 Lab - Mission Answers

> **Student Name:** _________________________
> **Student ID:** _________________________
> **Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **Hardcoded API key** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` nằm ngay trong source code. Nếu push lên GitHub, key bị lộ ngay lập tức.
2. **Hardcoded database credentials** — `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"` chứa username/password trực tiếp.
3. **Không có config management** — `DEBUG = True` và `MAX_TOKENS = 500` hardcode, không đọc từ environment variables.
4. **Print thay vì structured logging** — dùng `print(f"[DEBUG] ...")` kể cả in ra secret (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`)
5. **Không có health check endpoint** — platform (Railway/Render/K8s) không biết container còn sống hay đã crash để restart.
6. **Port cố định, host là localhost** — `host="localhost"` chỉ chạy được trên máy local, `port=8000` cứng không đọc `$PORT` env var (Railway/Render inject qua env).
7. **Debug reload trong production** — `reload=True` không nên bật ở production (tiêu tốn tài nguyên, không ổn định).
8. **Không có graceful shutdown** — không xử lý SIGTERM, khi container bị kill sẽ mất request đang xử lý.

### Exercise 1.3: Comparison table

| Feature | Develop (basic) | Production (advanced) | Why Important? |
|---------|----------------|----------------------|----------------|
| Config | Hardcode trong code | Env vars (12-factor) | Dễ thay đổi per environment, không lộ secrets |
| Health check | ❌ Không có | ✅ `GET /health` | Platform biết khi nào restart container |
| Logging | `print()` (debug) | JSON structured logging | Dễ parse, filter, aggregate trong ELK/CloudWatch |
| Shutdown | Đột ngột (kill process) | Graceful (SIGTERM handler) | Hoàn thành request đang xử lý trước khi tắt |
| Security | Không auth | API Key authentication | Chặn truy cập trái phép, kiểm soát chi phí |
| Host binding | `localhost` only | `0.0.0.0` | Container/cloud cần bind all interfaces |
| Port | Hardcode `8000` | Đọc từ `$PORT` env | Cloud platforms inject port qua env var |
| Secrets | Trong source code | `.env` file (gitignored) | Tránh lộ credentials khi push code |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11` (full distribution, ~1 GB)
2. **Working directory:** `/app` (`WORKDIR /app`)
3. **Tại sao COPY requirements.txt trước?** — Docker layer caching. Nếu requirements.txt không đổi, Docker dùng lại cached layer của `pip install` → build nhanh hơn nhiều. Chỉ khi code thay đổi mới rebuild layers sau đó.
4. **CMD vs ENTRYPOINT:**
   - `CMD` — default command, có thể bị override bởi `docker run <image> <command>`
   - `ENTRYPOINT` — luôn chạy, không bị override (trừ khi dùng `--entrypoint`). Thường dùng khi container có 1 nhiệm vụ duy nhất.
   - Kết hợp: `ENTRYPOINT ["python"]` + `CMD ["app.py"]` → có thể override argument nhưng vẫn chạy python.

### Exercise 2.3: Image size comparison

- **Develop (single-stage, python:3.11):** ~1000+ MB (full Python distribution + build tools)
- **Production (multi-stage, python:3.11-slim):** ~300-400 MB (chỉ runtime, không có gcc/build tools)
- **Difference:** ~60-70% smaller

**Multi-stage build hoạt động thế nào:**
- **Stage 1 (builder):** Cài gcc, libpq-dev, compile dependencies → image lớn nhưng chỉ dùng để build
- **Stage 2 (runtime):** Chỉ COPY installed packages từ builder, không kèm build tools → image nhỏ, sạch, secure hơn

### Exercise 2.4: Docker Compose architecture

Services được start: `agent`, `redis`, `nginx` (load balancer)

Communication flow:
```
Client → Nginx (:80) → Agent (:8000) → Redis (:6379)
```

- Nginx reverse proxy nhận traffic từ ngoài, forward đến agent instances
- Agent đọc/ghi state vào Redis (conversation history, rate limit, cost)
- Tất cả trong cùng Docker network nội bộ, chỉ Nginx expose ra ngoài

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** `https://agent-api-production-dae1.up.railway.app`
- **Deployed status:** ✅ Running (health + ready + ask tested successfully)
- **Steps thực hiện:**
  1. `npm i -g @railway/cli` — cài CLI
  2. `railway login` — xác thực
  3. `railway init` — tạo project
  4. `railway variables set PORT=8000 AGENT_API_KEY=<secret> REDIS_URL=<redis-url>`
  5. `railway up` — deploy
  6. `railway domain` — lấy public URL
- **Config file:** `railway.toml` dùng DOCKERFILE builder, health check `/health`, restart on failure.

### Exercise 3.2: Render deployment

- So sánh `render.yaml` vs `railway.toml`:

| Aspect | railway.toml | render.yaml |
|--------|-------------|-------------|
| Format | TOML | YAML |
| Builder | Dockerfile | Docker / Native runtime |
| Env vars | CLI (`railway variables set`) | Trong YAML hoặc Dashboard |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Auto deploy | Mặc định có | `autoDeploy: true` |
| Region | Auto | Chọn được (e.g., singapore) |
| Secrets | CLI | `generateValue: true` trong YAML |

### Exercise 3.3: (Optional) GCP Cloud Run

- `cloudbuild.yaml` — CI/CD pipeline: build Docker image → push lên Container Registry → deploy lên Cloud Run
- `service.yaml` — Cloud Run service config: min/max instances, memory, CPU, env vars, traffic routing
- Cloud Run ưu điểm: scale to zero (0 cost khi không có traffic), 2M free requests/month

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

**4.1 — API Key Authentication:**
- API key được check trong middleware/dependency qua header `X-API-Key`
- Sai key → HTTP 401 Unauthorized
- Rotate key: đổi environment variable `AGENT_API_KEY` rồi restart service

**Without key:**
```
$ curl http://localhost:8000/ask -X POST -H "Content-Type: application/json" -d '{"question":"Hello"}'
→ 401 {"detail": "Invalid or missing API key. Include header: X-API-Key: <key>"}
```

**With key:**
```
$ curl http://localhost:8000/ask -X POST -H "X-API-Key: test-api-key-local" -H "Content-Type: application/json" -d '{"question":"Hello"}'
→ 200 {"question":"Hello","answer":"...","model":"gpt-4o-mini",...}
```

**4.2 — Rate Limiting:**
- Algorithm: **Sliding Window Counter** (sorted set in Redis)
- Limit: **10 requests/minute** per user
- Khi vượt limit → HTTP 429 Too Many Requests, header `Retry-After: 60`

**Test 15 requests liên tục:**
```
Request 1-10: 200 OK
Request 11-15: 429 {"detail": "Rate limit exceeded: 10 req/min. Try again later."}
```

### Exercise 4.4: Cost guard implementation

**Approach:** Redis-backed monthly budget tracking per user.

```python
def check_budget(user_key: str, estimated_cost: float) -> None:
    month_key = datetime.utcnow().strftime("%Y-%m")
    budget_key = f"budget:{user_key}:{month_key}"
    current = float(redis.get(budget_key) or 0)
    if current + estimated_cost > 10.0:  # $10/month
        raise HTTPException(402, "Monthly budget exceeded")

def record_cost(user_key: str, cost: float) -> None:
    redis.incrbyfloat(budget_key, cost)
    redis.expire(budget_key, 32 * 24 * 3600)  # auto-expire after 32 days
```

**Logic:** Mỗi user có budget $10/tháng. Key Redis theo format `budget:{user}:{YYYY-MM}`. Tự reset đầu tháng mới (key mới). TTL 32 ngày để Redis tự cleanup.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health & Readiness checks

**Health (Liveness probe)** — `/health`:
- Trả 200 nếu process còn sống
- Platform (Docker/K8s) restart container nếu health check fail liên tục

**Ready (Readiness probe)** — `/ready`:
- Trả 200 nếu app sẵn sàng nhận traffic
- **Kiểm tra Redis connectivity** (ping) — nếu Redis down → 503
- Load balancer ngừng route traffic đến instance chưa ready

```python
@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    redis.ping()  # verify Redis connection
    return {"ready": True, "redis": "ok"}
```

### Exercise 5.2: Graceful shutdown

```python
def _handle_signal(signum, _frame):
    global _is_ready
    logger.info(json.dumps({"event": "SIGTERM_received"}))
    _is_ready = False  # /ready trả 503 → LB ngừng gửi traffic mới
    # uvicorn's timeout_graceful_shutdown=30 → đợi 30s cho request đang xử lý xong

signal.signal(signal.SIGTERM, _handle_signal)
```

**Flow:** SIGTERM → set `_is_ready=False` → LB ngừng route traffic → uvicorn đợi 30s cho in-flight requests → shutdown clean.

### Exercise 5.3: Stateless design

**Anti-pattern:** `conversation_history = {}` trong memory → mất khi restart, mỗi instance có data riêng khi scale.

**Correct:** Dùng Redis cho tất cả state:
- **Conversation history:** `history:{user_id}` — Redis list
- **Rate limit:** `ratelimit:{user_id}` — Redis sorted set
- **Cost tracking:** `budget:{user_id}:{month}` — Redis string

→ Scale ra bao nhiêu instances cũng chia sẻ chung state qua Redis.

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
```

- 3 agent instances cùng connect đến 1 Redis
- Nginx round-robin phân tán requests
- Nếu 1 instance die → health check fail → Nginx tự loại khỏi pool

### Exercise 5.5: Stateless test notes

- Tạo conversation trên instance A
- Kill instance A
- Gọi tiếp → request đến instance B → conversation history vẫn còn (vì lưu trong Redis)
- ✅ Chứng minh stateless design hoạt động đúng

---

_End of Mission Answers_
