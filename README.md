# Flash Sale Engine

A high-concurrency flash-sale backend built with FastAPI, Redis, and PostgreSQL. Uses Redis atomic operations (`DECR`, `SETEX`) to prevent overselling and duplicate purchases under burst traffic, with JWT-based auth and async order persistence.

## Features

- **Atomic Stock Management** — Redis `DECR` prevents race conditions on stock counts across concurrent requests.
- **Duplicate-Purchase Lock** — Redis `SETEX` lease (`lease:{user_id}`, 10s TTL) blocks a user from double-submitting a purchase while one is in flight.
- **One Flash Item Per Day** — `purchased_flash:{user_id}` key limits each user to one flash-sale item per day.
- **Rollback on Partial Failure** — if any item in a multi-item order is out of stock, previously decremented stock for that order is restored.
- **Anti-Bot Challenge** — requires users to solve a math challenge (`/buy/challenge`) before purchasing, preventing script spam.
- **Rate Limiting** — strict rate limiters on login and purchase endpoints to prevent abuse.
- **JWT Authentication** — stateless auth via PyJWT, with `asyncio.to_thread` for non-blocking bcrypt password hashing.
- **Role-Based Admin Routes** — secure `/admin/*` routes checking Postgres `users` table.
- **Async Order Persistence** — background `asyncio` task writes to Postgres via SQLAlchemy (async) so the user gets a 200 OK instantly.
- **Database Migrations** — Alembic is configured for programmatic migrations on startup.
- **Dockerized** — FastAPI (multi-worker) + Postgres + Redis via `docker-compose`.

## Tech Stack

| Layer | Tools |
| :--- | :--- |
| **API** | FastAPI, Pydantic, Uvicorn |
| **Cache / Locking** | Redis |
| **Database** | PostgreSQL, SQLAlchemy (async), asyncpg, Alembic |
| **Auth** | PyJWT, bcrypt |
| **Testing** | Pytest, Locust |
| **Code Quality** | Ruff, pre-commit |
| **Containerization** | Docker, Docker Compose |

## Setup & Run

### 1. Clone and configure

```bash
git clone https://github.com/naina-sriv/flash-sale-engine.git
cd flash-sale-engine
```

Create a `.env` file:
```
SECRET_KEY=your-secret-key
ALGORITHM=HS256
```

### 2. Run with Docker Compose

```bash
docker compose up --build -d
```

### 3. Load Testing

A Locust load test is included to verify the concurrency model. It tests the raw Redis throughput.

```bash
python -m locust -f stress_locustfile.py --headless -u 1000 -r 200 --run-time 30s -H http://localhost:8000
```
On a local machine, the API typically handles ~500+ Requests Per Second (RPS) before CPU throttling kicks in, demonstrating the robustness of the Redis lock-free atomic decrements.

## API Endpoints

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/auth/signup` | POST | — | Registers a new user |
| `/auth/login` | POST | — | Returns a JWT |
| `/buy/challenge` | GET | JWT | Returns a math challenge question |
| `/buy/` | POST | JWT | Submits challenge answer and reserves item(s) |
| `/buy/stress` | POST | — | Raw performance testing endpoint |
| `/stock/` | GET | — | Returns current Redis stock counts |
| `/stock/set` | POST | JWT + admin | Sets stock manually |
| `/admin/flash/add` | POST | JWT + admin | Adds an item to the flash sale |
| `/admin/flash/remove`| POST | JWT + admin | Removes an item from the flash sale |
| `/admin/flash/list` | GET | JWT + admin | Lists current flash-sale items |