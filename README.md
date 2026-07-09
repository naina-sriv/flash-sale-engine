# Flash Sale Engine

A high-concurrency flash-sale backend built with FastAPI, Redis, and PostgreSQL. Uses Redis atomic operations (`DECR`, `SETEX`) to prevent overselling and duplicate purchases under burst traffic, with JWT-based auth and async order persistence.

> Note: this is a work-in-progress learning project, not a production system. See [Known Limitations](#known-limitations) below for what's not solved yet.

## Features

- **Atomic Stock Management** — Redis `DECR` prevents race conditions on stock counts across concurrent requests.
- **Duplicate-Purchase Lock** — Redis `SETEX` lease (`lease:{user_id}`, 10s TTL) blocks a user from double-submitting a purchase while one is in flight.
- **One Flash Item Per Day** — `purchased_flash:{user_id}` key (24.8h TTL) limits each user to one flash-sale item per day.
- **Rollback on Partial Failure** — if any item in a multi-item order is out of stock, previously decremented stock for that order is restored.
- **JWT Authentication** — stateless auth via PyJWT (HS256), with bcrypt password hashing on login.
- **Role-Based Admin Routes** — `/admin/*` routes check `role == "admin"` against the Postgres `users` table.
- **Async Order Persistence** — background `asyncio` task simulates a 3-second payment step, then writes to Postgres via SQLAlchemy (async).
- **Dockerized** — FastAPI + Postgres + Redis via `docker-compose`, with healthchecks gating service startup order.

## Tech Stack

| Layer | Tools |
| :--- | :--- |
| **API** | FastAPI, Pydantic, Uvicorn |
| **Cache / Locking** | Redis |
| **Database** | PostgreSQL, SQLAlchemy (async), asyncpg |
| **Auth** | PyJWT (HS256), bcrypt |
| **Async** | asyncio (`create_task` for background payment simulation) |
| **Containerization** | Docker, Docker Compose |

## Project Structure

```
flash-sale-engine/
├── main.py                     # FastAPI app entrypoint, router registration, startup hook
├── src/
│   ├── core/
│   │   ├── config.py           # Env vars: SECRET_KEY, ALGORITHM, REDIS_HOST/PORT, DATABASE_URL
│   │   ├── db.py                # Async SQLAlchemy engine, session factory, Base
│   │   └── redis_client.py     # Redis connection
│   ├── dependencies/
│   │   └── auth.py             # get_current_user (JWT decode), require_admin (DB role check)
│   ├── models/
│   │   ├── items.py            # ItemRequest (admin stock add/remove)
│   │   └── requests.py         # BuyRequest, LoginRequest
│   ├── routes/
│   │   ├── admin.py            # POST /admin/flash/add, /admin/flash/remove, GET /admin/flash/list
│   │   ├── auth.py             # POST /auth/login
│   │   ├── buy.py              # POST /buy/
│   │   └── stock.py            # GET /stock/, POST /stock/set
│   └── schema/
│       └── db_models.py        # User, Product, Order (SQLAlchemy models)
├── Dockerfile
├── docker-compose.yml           # postgres + redis + api, with healthcheck-gated startup
├── requirements.txt
└── .gitignore
```

## Setup & Run

### Prerequisites
- Docker & Docker Compose
- A `.env` file at the repo root (gitignored — the Dockerfile copies it in, so it must exist locally before building)

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
docker-compose up --build
```

This starts Postgres, Redis, and the API (port `8000`), in that dependency order via healthchecks. On startup, the app seeds Redis with sample stock:
- `stock:1 = 10`, `stock:2 = 12`, `stock:3 = 3`
- `flash_items = {1, 3}`

### 3. Try it

```bash
# Login (requires a user already in the users table — no signup route exists yet)
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'

# Buy (item 1 or 3 are flash items per the seed data)
curl -X POST "http://localhost:8000/buy/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token_from_login>" \
  -d '{"user_id":"1","item_id":["1"]}'

# Check stock
curl "http://localhost:8000/stock/"
```

## API Endpoints

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/auth/login` | POST | — | Returns a JWT for a registered user |
| `/buy/` | POST | JWT | Attempts to reserve item(s); rejects duplicates, enforces one-flash-item-per-day |
| `/stock/` | GET | — | Returns current Redis stock counts for all `stock:*` keys |
| `/stock/set` | POST | JWT (broken, see below) | Intended to let admins set stock manually |
| `/admin/flash/add` | POST | JWT + admin role | Adds an item to the flash sale set with initial stock |
| `/admin/flash/remove` | POST | JWT + admin role | Removes an item from the flash sale set |
| `/admin/flash/list` | GET | JWT + admin role | Lists current flash-sale item IDs |

## Known Limitations

Documenting these here deliberately rather than glossing over them:

- **`/stock/set`'s admin check is broken.** It compares the JWT's numeric `user_id` to the literal string `"admin"`, which will never match. Use `/admin/flash/add` instead — it correctly checks `role` against the `users` table via `require_admin`.
- **Multi-item orders only persist the last item.** In `buy.py`'s `process_payment`, the `Order` row is built inside the loop but added/committed outside it, so only the final item in a multi-item purchase gets written to Postgres.
- **JWTs don't expire.** No `exp` claim is set on issue, so tokens are valid indefinitely unless `SECRET_KEY` is rotated.
- **`requirements.txt` is UTF-16 encoded.** It needs to be re-saved as UTF-8 before `pip install -r requirements.txt` will reliably work on most setups.
- **No Nginx, rate-limiting, or anti-bot protection yet** — despite what earlier drafts of this README claimed. These are on the roadmap, not in the code.
- **No signup route** — users must currently be inserted into the `users` table directly.

## Roadmap

- Fix the two bugs above (multi-item order persistence, `/stock/set` admin check)
- Add a signup endpoint and password reset flow
- Add Nginx reverse proxy for horizontal scaling across multiple API replicas
- Add rate-limiting (e.g. `slowapi`) and basic anti-bot checks on `/buy/`
- Add token expiry + refresh flow
- Load testing with Locust to validate behavior under actual burst traffic

## Acknowledgements

- Inspired by Savana's "One Rupee, One Impact" flash-sale campaign model.