# 🌍 AML Geographic Risk Screening API

A lightweight FastAPI service that assesses transaction risk based on geographic mismatch between a user's registered country and their current IP location.

## ✅ Features

- **4-tier risk scoring**: Low, Medium, High, Critical
- **Real-time GeoIP lookup** using ip-api.com
- **Country mismatch detection** with neighboring country logic
- **High-risk jurisdiction flagging** (FATF-based)
- **Interactive API docs** via Swagger UI

> ⚠️ **V1**: No auth, no database, no rate limiting

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn httpx pydantic pydantic-settings python-dotenv
```

### 2. Create `.env`

```env
APP_NAME=AML Screening API
VERSION=1.0.0
GEOIP_API_URL=http://ip-api.com/json
API_PREFIX=/api/v1
PORT=8000
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

### 4. Test

```bash
curl -X POST http://localhost:8000/api/v1/screen \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN001",
    "user_id": "USER123",
    "user_country": "US",
    "ip_address": "8.8.8.8"
  }'
```

**Docs**: http://localhost:8000/api/v1/docs

---

## 📊 Risk Logic

| Scenario | Risk Level | Score | Action |
|----------|------------|-------|--------|
| Same country | Low | 0 | ✅ Allow |
| Neighboring countries | Medium | 20-30 | ✅ Allow + log |
| Different regions | High | 50-70 | ⚠️ Flag |
| High-risk country | Critical | 100 | ❌ Block |

**High-risk countries**: IR, PK, AF, KP, MM, SY, YE (FATF-based)

---

## 📡 API Endpoints

### `POST /api/v1/screen`

**Request:**
```json
{
  "transaction_id": "TXN001",
  "user_id": "USER123",
  "user_country": "US",
  "ip_address": "8.8.8.8"
}
```

**Response:**
```json
{
  "transaction_id": "TXN001",
  "risk_score": 0,
  "risk_level": "LOW",
  "should_block": false,
  "user_country": "US",
  "ip_country": "US",
  "triggered_rules": []
}
```

### `GET /api/v1/health`

Returns `{"status": "healthy", "version": "1.0.0"}`

---

## 🧭 Roadmap

**Phase 2**: Database persistence, transaction history  
**Phase 3**: API key auth, rate limiting, multi-tenancy  
**Phase 4**: VPN detection, velocity checks, ML models

---

## 📄 License

MIT License - Free to use and modify

---

> 💡 **Built for real-world AML use cases**  
> Start simple. Iterate fast.