# Local Testing Guide - LLM Council API

## 🧪 Complete Testing Instructions

### Prerequisites
```bash
# Check Python version (3.10+ required)
python3 --version

# Check if MongoDB is installed
mongod --version

# Check if Redis is installed (optional but recommended)
redis-cli --version
```

---

## Step 1: Install Dependencies

```bash
cd llm-council-api

# Install all production dependencies
pip install -r requirements.txt

# Should install:
# - fastapi, uvicorn (web framework)
# - motor (MongoDB async driver)
# - httpx (HTTP client with connection pooling)
# - redis, hiredis (caching)
# - pybreaker (circuit breaker)
# - prometheus-client (metrics)
```

---

## Step 2: Start Infrastructure

### Option A: Using Docker (Recommended)
```bash
# Start MongoDB + Redis with docker-compose
docker-compose up -d mongodb redis

# Check if running
docker ps
```

### Option B: Manual Setup

**Start MongoDB:**
```bash
# macOS/Linux
mongod --dbpath ~/data/db

# Or use system service
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS
```

**Start Redis:**
```bash
# macOS/Linux
redis-server

# Or use system service
sudo systemctl start redis  # Linux
brew services start redis  # macOS
```

**Verify Services:**
```bash
# Test MongoDB
mongosh --eval "db.runCommand({ ping: 1 })"
# Should return: { ok: 1 }

# Test Redis
redis-cli ping
# Should return: PONG
```

---

## Step 3: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your settings
nano .env  # or use your favorite editor
```

**Minimal .env for testing:**
```bash
OPENROUTER_API_KEY=your_key_here
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=llm_council_test
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true
ENVIRONMENT=development
```

Get OpenRouter key: https://openrouter.ai/keys

---

## Step 4: Start the API

```bash
# Development mode (auto-reload)
uvicorn main:app --reload --port 8000

# Or with multiple workers (production-like)
uvicorn main:app --workers 4 --port 8000
```

**You should see:**
```
LLM Council API starting...
Council members: ['NVIDIA Nemotron 9B', 'Llama 3.2 3B', 'Phi-3 Mini', 'GPT OSS 20B']
Chairman: Qwen 2 7B
Metrics initialized
Connecting to MongoDB...
MongoDB connected successfully
MongoDB indexes ensured
Redis connected: redis://localhost:6379/0
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Step 5: Test Health Checks

### Test 1: Liveness Probe
```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "service": "llm-council-api"
}
```

### Test 2: Readiness Probe
```bash
curl http://localhost:8000/ready
```

**Expected:**
```json
{
  "status": "ready",
  "checks": {
    "mongodb": "healthy",
    "redis": "healthy",
    "circuit_breaker": "closed"
  }
}
```

**If Redis is disabled:**
```json
{
  "checks": {
    "mongodb": "healthy",
    "redis": "disabled",
    "circuit_breaker": "closed"
  }
}
```

---

## Step 6: Test Core Functionality

### Test 3: Create a Session
```bash
curl -X POST http://localhost:8000/session \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the top 3 benefits of using async programming in Python?",
    "mode": "formal"
  }'
```

**Expected:**
```json
{
  "session": {
    "id": "abc-123-def-456",
    "version": 1,
    "title": "What are the top 3 benefits...",
    "rounds": [{"question": "...", "status": "pending"}]
  },
  "message": "Session created in formal council mode..."
}
```

**Save the session ID!**

### Test 4: Run Council (Full Process)
```bash
# Replace SESSION_ID with the ID from Test 3
curl -X POST http://localhost:8000/session/SESSION_ID/run-all
```

**Expected (takes 10-15 seconds):**
```json
{
  "session": {
    "rounds": [{
      "responses": [
        {"model_name": "NVIDIA Nemotron 9B", "response": "..."},
        {"model_name": "Llama 3.2 3B", "response": "..."}
      ],
      "peer_reviews": [...],
      "final_synthesis": "Based on the council discussion...",
      "status": "synthesized"
    }]
  }
}
```

### Test 5: Get Session (Test Caching)
```bash
# First request (cache miss)
time curl http://localhost:8000/session/SESSION_ID

# Second request (cache hit - should be much faster!)
time curl http://localhost:8000/session/SESSION_ID
```

**Expected:**
- First request: ~50-100ms
- Second request: ~5-10ms (cached!)

---

## Step 7: Test Production Features

### Test 6: Rate Limiting
```bash
# Spam requests to trigger rate limit
for i in {1..110}; do
  curl http://localhost:8000/session/SESSION_ID
done
```

**Expected (after 100 requests):**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds. Remaining: 0"
}
```

**Response Headers:**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Remaining: 0
```

### Test 7: Circuit Breaker

**Simulate OpenRouter failure:**
```bash
# Set invalid API key in .env
OPENROUTER_API_KEY=invalid_key

# Restart API

# Try to run council 5+ times
for i in {1..6}; do
  curl -X POST http://localhost:8000/session/SESSION_ID/run-all
done
```

**Expected (after 5 failures):**
```json
{
  "detail": "Service temporarily unavailable (circuit breaker open)"
}
```

**Check circuit breaker status:**
```bash
curl http://localhost:8000/ready
```

**Expected:**
```json
{
  "status": "not_ready",
  "checks": {
    "circuit_breaker": "open"
  }
}
```

### Test 8: Optimistic Locking (Race Condition Prevention)

**Terminal 1:**
```bash
# Get session
SESSION=$(curl http://localhost:8000/session/SESSION_ID)

# Update title (will take a few seconds)
sleep 3 && curl -X PATCH http://localhost:8000/session/SESSION_ID \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"title": "Updated from Terminal 1"}'
```

**Terminal 2 (run immediately after Terminal 1):**
```bash
# Try to update at the same time
curl -X PATCH http://localhost:8000/session/SESSION_ID \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"title": "Updated from Terminal 2"}'
```

**Expected (one will succeed, other will fail):**
```json
{
  "detail": "Session abc-123 was modified by another request. Please refresh and try again."
}
```

**HTTP Status:** `409 Conflict`

---

## Step 8: Test Monitoring

### Test 9: Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

**Expected (sample):**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/session/abc123",method="GET",status="200"} 5.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/session",method="POST",le="0.1"} 10.0

# HELP cache_operations_total Cache operations
# TYPE cache_operations_total counter
cache_operations_total{operation="get",result="hit"} 42.0
cache_operations_total{operation="get",result="miss"} 8.0
```

### Test 10: Cache Performance

**Test cache hit rate:**
```bash
# Create session
SESSION_ID=$(curl -X POST http://localhost:8000/session \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}' | jq -r '.session.id')

# Get 10 times (should be fast after first)
for i in {1..10}; do
  time curl -s http://localhost:8000/session/$SESSION_ID > /dev/null
done

# Check cache metrics
curl http://localhost:8000/metrics | grep cache_operations_total
```

**Expected:**
- 1 cache miss, 9 cache hits
- Latency: First ~50ms, rest ~5ms

---

## Step 9: Redis Testing (Optional)

### Test 11: Redis Failover

**Stop Redis:**
```bash
# Stop Redis
docker stop redis  # or: sudo systemctl stop redis
```

**Make requests:**
```bash
curl http://localhost:8000/session/SESSION_ID
```

**Expected:**
- API still works! ✅
- Falls back to in-memory cache
- Logs show: "Redis unavailable - using in-memory cache fallback"

**Restart Redis:**
```bash
docker start redis
# API automatically reconnects!
```

---

## Step 10: Load Testing (Optional)

### Test 12: Stress Test

**Install hey (load testing tool):**
```bash
# macOS
brew install hey

# Linux
go install github.com/rakyll/hey@latest
```

**Run load test:**
```bash
# 1000 requests, 50 concurrent
hey -n 1000 -c 50 http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics | grep http_requests_total
```

**Expected:**
- All requests succeed (200 OK)
- P95 latency < 50ms for /health
- No errors in logs

---

## Troubleshooting

### Issue: API won't start

**Check:**
```bash
# MongoDB running?
mongosh --eval "db.runCommand({ ping: 1 })"

# Port 8000 already in use?
lsof -i :8000
# Kill if needed: kill -9 PID

# Dependencies installed?
pip list | grep -E "fastapi|motor|redis"
```

### Issue: Circuit breaker opens immediately

**Check:**
```bash
# Valid OpenRouter key?
curl -H "Authorization: Bearer YOUR_KEY" \
  https://openrouter.ai/api/v1/models

# Network connection?
ping openrouter.ai
```

### Issue: Cache not working

**Check:**
```bash
# Redis connected?
redis-cli ping

# Cache enabled?
grep REDIS_ENABLED .env

# Check logs
# Should see: "Redis connected: redis://..."
# Not: "Redis unavailable"
```

### Issue: Tests fail with "Module not found"

```bash
# Make sure you're in the right directory
cd llm-council-api

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python3 -c "import sys; print(sys.path)"
```

---

## Quick Test Script

Save as `test_all.sh`:
```bash
#!/bin/bash
set -e

echo "🧪 Testing LLM Council API..."

echo "\n✓ Test 1: Health Check"
curl -f http://localhost:8000/health || exit 1

echo "\n✓ Test 2: Ready Check"
curl -f http://localhost:8000/ready || exit 1

echo "\n✓ Test 3: Create Session"
SESSION_ID=$(curl -s -X POST http://localhost:8000/session \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}' | jq -r '.session.id')

echo "\n✓ Test 4: Get Session"
curl -f http://localhost:8000/session/$SESSION_ID || exit 1

echo "\n✓ Test 5: Cache Hit"
curl -f http://localhost:8000/session/$SESSION_ID || exit 1

echo "\n✓ Test 6: Metrics"
curl -f http://localhost:8000/metrics | grep -q "http_requests_total" || exit 1

echo "\n\n✅ All tests passed!"
```

Run it:
```bash
chmod +x test_all.sh
./test_all.sh
```

---

## Expected Performance Benchmarks

With all optimizations:

| Endpoint | First Call | Cached | Target |
|----------|-----------|--------|--------|
| `/health` | 5ms | 5ms | < 10ms |
| `/ready` | 50ms | 50ms | < 100ms |
| `/session/{id}` | 80ms | 5ms | < 100ms |
| `/session` (create) | 50ms | - | < 100ms |
| `/session/{id}/run-all` | 12s | - | < 20s |

---

## What to Look For

### ✅ Good Signs:
- "Redis connected" in startup logs
- "MongoDB indexes ensured"
- `/ready` returns `"status": "ready"`
- Cache hit rate > 80% after warmup
- P95 latency < 100ms for GET endpoints
- No errors in Prometheus metrics

### ⚠️ Warning Signs:
- "Redis unavailable" (still works, but no distributed cache)
- Circuit breaker state "open" (OpenRouter API issues)
- High rate limit hits (adjust `RATE_LIMIT_REQUESTS`)
- Version conflicts (multiple concurrent updates)

### 🚨 Red Flags:
- MongoDB connection failed
- Cannot bind to port 8000
- Import errors (missing dependencies)
- Constant 500 errors

---

## Next Steps

1. **Run all tests above** ✅
2. **Check Prometheus metrics** at `/metrics`
3. **Monitor logs** for errors
4. **Test with real traffic** using Postman/curl
5. **Deploy to production** (see PRODUCTION.md)

Need help? Check logs or create GitHub issue!
