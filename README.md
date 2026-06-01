# ☕ Café Management API

A backend MVP for managing café operations — orders, billing, and AI-powered inventory scanning — built with **FastAPI** and **SQLite**, with a custom frontend UI.

## Demo

Watch the demo video here: [Café Management API Demo](https://drive.google.com/file/d/11A7Xq2ymOZ933OyvIhfdNEpzaGni_1v9/view?usp=drive_link)

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Validation | Pydantic v2 |
| AI Vision | Anthropic Claude Haiku |
| Runtime | Uvicorn |
| Container | Docker + Compose |

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd cafe-api

# 2. Set your Anthropic API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run
docker compose up --build
```

Visit: **http://localhost:8000** → opens the UI  
API docs: **http://localhost:8000/docs**

---

### Option 2 — Local (Python 3.12+)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=your_key_here

uvicorn app.main:app --reload
```

---

## API Overview

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/orders/` | Create a new order with items |
| `GET` | `/orders/` | List all orders (filter by `?status_filter=pending`) |
| `GET` | `/orders/{id}` | Get a specific order |
| `PATCH` | `/orders/{id}/status` | Advance order status |
| `DELETE` | `/orders/{id}` | Delete a pending order |

**Status flow:** `pending → preparing → done` (enforced — no skipping)

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/billing/invoice/{order_id}` | Generate invoice with tax + discount |
| `GET` | `/billing/invoice/{order_id}` | Fetch existing invoice |
| `GET` | `/billing/invoices` | List all invoices |

**Discount types:** `percentage` (e.g. 10%) or `fixed` (e.g. ₹50 flat)  
**Tax:** flat % applied after discount

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/inventory/scan` | Upload image → AI identifies → logs to inventory |
| `GET` | `/inventory/` | List all inventory items |
| `GET` | `/inventory/{id}` | Get a specific item |
| `PATCH` | `/inventory/{id}` | Update item name or quantity |
| `DELETE` | `/inventory/{id}` | Remove item (also deletes image) |

---

## Design Decisions

### 1. FastAPI + SQLite — intentional simplicity
SQLite removes the need for a separate database container, making `docker compose up` truly one-command. For a production system I'd swap in PostgreSQL with Alembic migrations. The SQLAlchemy ORM layer means this swap is a one-line config change (`DATABASE_URL`).

### 2. Status transitions are enforced server-side
The `PATCH /orders/{id}/status` endpoint only accepts the *next valid* state. Clients can't jump from `pending` to `done`. This prevents silent data corruption and makes the state machine explicit.

### 3. Invoice is immutable and idempotent
Once an invoice is created for an order, it can't be regenerated (returns `409`). This mirrors real billing behaviour — you can't silently reissue an invoice. The trade-off is that you'd need a "credit note" pattern for corrections in production.

### 4. Billing calculation order
`subtotal → discount → tax` (tax on the discounted price, not the original). This matches standard GST behaviour in India. I made this explicit in the code rather than leaving it implicit.

### 5. AI Vision uses Claude Haiku
`claude-haiku-4-5` is the fastest and most cost-effective Claude model — ideal for real-time image scanning. The prompt constrains output to strict JSON, with a fallback parser if the model deviates. The raw response is stored in the DB for debugging.

### 6. Uploaded images are persisted
Images are stored in an `uploads/` directory mapped to a Docker volume. The filename is a UUID to avoid collisions and prevent path traversal attacks. Deleting an inventory item also cleans up its image.

### 7. Frontend is served from the same container
A single `docker compose up` gives you both the API and a working UI at port 8000. No separate frontend container needed for an MVP.

---

## What I'd Improve With More Time

- **PostgreSQL + Alembic** — proper migrations instead of `create_all`
- **Auth** — JWT-based authentication; currently the API is fully open
- **Pagination** — cursor-based pagination for large order/inventory lists
- **Invoice PDF export** — generate downloadable PDFs using WeasyPrint
- **Websockets** — real-time order status updates pushed to the kitchen UI
- **Item quantity management** — auto-decrement inventory when an order is placed
- **Tests** — pytest suite covering the billing calculation logic, status transitions, and the AI fallback path
