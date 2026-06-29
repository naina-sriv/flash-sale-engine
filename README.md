# Flash Sale Engine

High‑concurrency flash sale system built with FastAPI, Redis, and stateless JWT authentication. Implements horizontal scaling via Docker & Nginx, rate‑limiting, and anti‑bot protections: designed to handle 1‑Rupee sale traffic without crashing the database.
---

##  Features

-  **Atomic Stock Management** – Redis `DECR` eliminates race conditions.
-  **Stateless JWT Authentication** – No database lookups; scales horizontally.
-  **Distributed Lease Lock** – Prevents duplicate purchases (5-minute payment hold).
-  **Daily Purchase Limit** – One flash item per user per day (24-hour lock).
-  **Asynchronous Payments** – Background task processing returns `"Reserved"` in < 50ms.
-  **Rollback on Failure** – Compensating transactions restore stock if any item fails.
-  **Modular Codebase** – Separation of routes, models, core, dependencies.
-  **Docker Ready** – Containerized with Redis for easy deployment.

---

##  Tech Stack

| Layer | Tools |
| :--- | :--- |
| **API** | FastAPI, Pydantic, Uvicorn |
| **Cache/State** | Redis (Docker) |
| **Auth** | PyJWT (HS256) |
| **Async** | asyncio |
| **Containerization** | Docker, Docker Compose |
| **Testing** | Locust (load testing) |

---

## Architecture Overview

```
┌──────────────┐
│   Client     │
│ (Browser/API)│
└──────┬───────┘
       │ (JWT in Header)
       ▼
┌─────────────────────────────────────────────┐
│              FastAPI Gateway                │
│  - Routes: /auth/login, /buy/, /stock       │
│  - Dependencies: get_current_user (JWT)     │
│  - Async Endpoints (async def)              │
└──────┬──────────────────┬───────────────────┘
       │                  │
       │ (Stock DECR)     │ (Lease SETEX)
       ▼                  ▼
┌──────────────┐    ┌─────────────────────┐
│    Redis     │    │   Redis (Lease)     │
│  stock:{id}  │    │ lease:{user_id}     │
│  atomic ops  │    │ purchased_flash:{}  │
└──────────────┘    └─────────────────────┘
       │
       │ (After payment success)
       ▼
┌─────────────────────────────────────────┐
│     Background Task (asyncio)           │
│  - Simulates 3-second payment gateway   │
│  - Prints "Payment successful"          │
│  - (Next: writes to SQLAlchemy DB)      │
└─────────────────────────────────────────┘
```

---

## 🛠️ Setup & Run

### Prerequisites

- Python 3.10+
- Redis (Docker recommended)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/flash-sale-engine.git
cd flash-sale-engine
```

### 2. Create a Virtual Environment & Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Sample `requirements.txt`:**
```
fastapi
uvicorn
redis
pyjwt
python-dotenv
httpx
asyncio
```

### 3. Environment Variables

Create a `.env` file in the project root:

```
SECRET_KEY=savana_mentor_super_secret_key_32chars
ALGORITHM=HS256
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4. Run Redis (Docker)

```bash
docker run -d -p 6379:6379 --name redis-flash redis:alpine
```

### 5. Start the FastAPI Server

```bash
uvicorn main:app --reload --port 5000
```

Server will be available at `http://localhost:5000` (Swagger at `/docs`).

---

## 📬 API Endpoints

### Authentication

| Endpoint | Method | Description | Request Body |
| :--- | :--- | :--- | :--- |
| `/auth/login` | POST | Login and receive JWT token | `{"user_id": "nain", "password": "admin123"}` |

**Response:**
```json
{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
```

### Flash Sale Purchase

| Endpoint | Method | Headers | Request Body |
| :--- | :--- | :--- | :--- |
| `/buy/` | POST | `Authorization: Bearer <token>` | `{"user_id": "nain", "item_id": ["1"]}` |

**Response:**
```json
{"message": "reserved"}
```

### Stock Check (Debug)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/stock/stock` | GET | Returns current Redis stock values |

---

## 🧪 Testing

### Manual Test with `curl`

```bash
# 1. Login
curl -X POST "http://localhost:5000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"nain","password":"admin123"}'

# 2. Copy the token, then buy
curl -X POST "http://localhost:5000/buy/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"user_id":"nain","item_id":["1"]}'
```

### Performance Measurement (PowerShell)

```powershell
$token = (Invoke-RestMethod -Uri "http://localhost:5000/auth/login" -Method Post -ContentType "application/json" -Body '{"user_id":"nain","password":"admin123"}').token

Measure-Command {
    Invoke-RestMethod -Uri "http://localhost:5000/buy/" -Method Post -Headers @{Authorization = "Bearer $token"} -Body '{"user_id":"nain","item_id":["2"]}' -ContentType "application/json"
}
```

**Expected response time:** < 50ms.

---

## Project Structure

```
flash-sale-engine/
├── app/
│   ├── core/
│   │   ├── config.py           # Env vars, SECRET_KEY
│   │   └── redis_client.py     # Redis connection
│   ├── dependencies/
│   │   └── auth.py             # get_current_user (JWT)
│   ├── models/
│   │   └── requests.py         # BuyRequest, LoginRequest (Pydantic)
│   ├── routes/
│   │   ├── buy.py              # POST /buy (flash sale logic)
│   │   ├── auth.py             # POST /auth/login
│   │   └── stock.py            # GET /stock
│   └── __init__.py
├── main.py                     # FastAPI app, include routers, startup
├── .env                        # Environment variables (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Security Considerations

- **JWT Secret**: Store `SECRET_KEY` in `.env` – never hardcode.
- **Password**: Currently hardcoded (`admin123`) – replace with hashed DB in production.
- **Lease TTL**: 5 minutes balances fairness and resource release.

---

## Future Improvements

- **Database Persistence**: Store orders in PostgreSQL after payment success.
- **Cart Management**: `POST /cart/add`, `GET /cart`, `DELETE /cart`.
- **Real Payment Gateway**: Integrate Razorpay/Stripe Webhooks.
- **Horizontal Scaling**: Add Nginx reverse proxy and multiple FastAPI replicas.
- **Observability**: Structured logging, Prometheus metrics.

---

## Key Design Decisions

- **Atomic Operations** – Redis `DECR` eliminates race conditions and prevents overselling.
- **Distributed Locks** – Redis `SETEX` with TTL handles payment holds and auto-releases inventory.
- **Async Processing** – `asyncio.create_task` keeps APIs responsive under load.
- **Stateless Authentication** – JWT allows horizontal scaling without session storage.
- **Modular Architecture** – Separation of routes, models, dependencies, and configuration.
- **Rollback Pattern** – Compensating transactions restore stock if any item fails.

---

## Acknowledgements

- **Savana** for the inspiration – the One Rupee One Impact campaign.
- **FastAPI** and **Redis** for the incredible developer experience.
