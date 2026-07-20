# Customer Support Ticket System

A role-based support-ticket platform: customers raise and track tickets,
support agents (admins) triage, respond, and resolve them from a
centralized dashboard with live analytics.

Built to demonstrate an FDSE-style skill set: a typed REST API, JWT-based
auth with proper role separation, a relational schema with real
constraints, and a frontend that talks to it over plain `fetch()` — no
framework magic, so the request/response contract is easy to trace end to end.

## Tech Stack

| Layer          | Choice                                                        |
|-----------------|----------------------------------------------------------------|
| Frontend        | HTML5, CSS3, Bootstrap 5, vanilla JavaScript (ES6), Fetch API, Chart.js |
| Backend         | Python, FastAPI, SQLAlchemy, Pydantic v2                       |
| Auth            | JWT (python-jose), bcrypt password hashing (Passlib)           |
| Database        | SQLite (dev, zero-config) / PostgreSQL (prod, via `DATABASE_URL`) |
| Server          | Uvicorn (ASGI)                                                 |

## Why these choices
- **FastAPI + Pydantic** gives request/response validation for free and
  generates interactive API docs (`/docs`) — useful both for frontend
  development and for demoing the API to non-engineers.
- **JWT** keeps the backend stateless: no server-side session store to
  scale, and the same token model works if this ever grows a mobile client.
- **Vanilla JS over a framework**: for a project this size, a build step
  buys nothing. Each page is a plain HTML file + one JS file, so anyone
  can open dev tools, watch the network tab, and see exactly what's
  happening.

## Roles

### Customer
Register, log in, create tickets (subject, description, priority, optional
attachment), view **only their own** tickets, edit a ticket while it's
still `Open`, delete their own ticket, reply in a ticket's comment thread,
and get a notification the moment an agent changes their ticket's status.

### Admin (Support Agent)
Log in separately, view **all** tickets, search/filter by customer,
subject, status, or priority, change status/priority, post public replies
or internal-only notes, delete any ticket, manage customer accounts
(delete / reset password), and read a live analytics dashboard.

## Project Structure
```
customer-support-ticket-system/
├── backend/
│   ├── app.py              # FastAPI app: CORS, routers, startup, admin seed
│   ├── database.py         # Engine/session (SQLite by default, Postgres via env var)
│   ├── models.py            # SQLAlchemy models: User, Ticket, Comment, Notification
│   ├── schemas.py            # Pydantic request/response models
│   ├── auth.py               # get_current_user / require_admin dependencies
│   ├── security.py           # Password hashing + JWT encode/decode
│   ├── crud.py                # All DB queries (routers never touch the ORM directly)
│   ├── utils.py                # File-upload validation/storage
│   ├── routers/
│   │   ├── auth.py              # POST /register, POST /login
│   │   ├── users.py              # GET /profile, GET/PUT /notifications
│   │   ├── tickets.py             # Ticket CRUD + comments (customer-scoped)
│   │   └── admin.py                # Admin ticket/user management + analytics
│   └── requirements.txt
├── frontend/
│   ├── index.html, login.html, register.html, dashboard.html,
│   │   create-ticket.html, ticket-details.html, admin.html, logout.html
│   ├── css/style.css
│   └── js/
│       ├── api.js          # fetch() wrapper: attaches JWT, handles 401s
│       ├── ui.js             # Toasts, confirm dialogs, badge/date helpers
│       ├── navbar.js          # Shared, role-aware navbar + notification bell
│       ├── dashboard.js, create-ticket.js, ticket-details.js, admin.js
└── README.md
```

## Getting Started

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
The API is now live at **http://127.0.0.1:8000** — interactive docs at
`/docs`. A SQLite file (`support_tickets.db`) and `uploads/` folder are
created automatically, along with a seeded admin account:

- **Email:** `admin@stv.local`
- **Password:** `Admin@123`

*(Change this before any real deployment — see Security Notes below.)*

### 2. Frontend
The frontend is static, so any local server works:
```bash
cd frontend
python -m http.server 5500
```
Open **http://127.0.0.1:5500**. If your API isn't on `127.0.0.1:8000`,
set `window.API_BASE_URL` at the top of the page (or edit the default in
`js/api.js`).

### 3. Production database
Set `DATABASE_URL` before starting the backend, e.g.:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/support_tickets"
```

## API Reference

### Authentication
| Method | Path       | Description                                   |
|--------|------------|------------------------------------------------|
| POST   | `/register`| Create a customer account                      |
| POST   | `/login`   | OAuth2 form login (`username`=email); returns JWT + role |
| GET    | `/profile` | Current user's profile (any authenticated role)|

### Customer — Tickets & Comments
| Method | Path                        | Description                                  |
|--------|------------------------------|------------------------------------------------|
| POST   | `/tickets`                   | Create a ticket (`multipart/form-data`, attachment optional) |
| GET    | `/tickets`                    | List **your own** tickets                       |
| GET    | `/tickets/{id}`                | View a ticket (owner or admin)                  |
| PUT    | `/tickets/{id}`                 | Edit subject/description — only while `Open`     |
| DELETE | `/tickets/{id}`                  | Delete your own ticket                          |
| POST   | `/tickets/{id}/comments`          | Reply on a ticket                                |
| GET    | `/tickets/{id}/comments`           | List replies (admins also see internal notes)     |

### Customer — Notifications
| Method | Path                              | Description                          |
|--------|-------------------------------------|------------------------------------------|
| GET    | `/notifications`                     | List your notifications                  |
| PUT    | `/notifications/{id}/read`             | Mark one as read                         |

### Admin
| Method | Path                                  | Description                            |
|--------|-----------------------------------------|--------------------------------------------|
| GET    | `/admin/tickets`                          | All tickets; filter via `?status=&priority=&customer_id=&search=` |
| PUT    | `/admin/tickets/{id}`                       | Update status/priority/assignee — notifies the customer on status change |
| DELETE | `/admin/tickets/{id}`                         | Delete any ticket                          |
| GET    | `/admin/users`                                  | List customers                             |
| DELETE | `/admin/users/{id}`                               | Delete a customer (cascades their tickets) |
| PUT    | `/admin/users/{id}/reset-password`                  | Generate a one-time temporary password     |
| GET    | `/admin/analytics`                                    | Dashboard stats: totals, status/priority breakdown, tickets/month, most active users |

## Authentication Flow
```
Register → Password hashed (bcrypt) → Stored in DB
Login → Credentials verified → JWT issued (sub=user_id, role)
Frontend stores the token → sends it as Authorization: Bearer <token>
FastAPI verifies the token → resolves the user → checks role → grants/denies access
```

## Security Notes
- Passwords are hashed with bcrypt; plaintext is never stored or logged.
- Role checks are enforced server-side (`require_admin` dependency) —
  hiding a button in the UI is never the only protection.
- SQL injection is not a concern here because every query goes through
  SQLAlchemy's ORM (no raw string-interpolated SQL).
- Uploads are restricted by extension whitelist and a 5 MB size cap, and
  stored under randomized filenames to avoid path traversal / overwrite.
- CORS is wide open (`*`) for local development — lock `ALLOWED_ORIGINS`
  down to your real frontend domain before deploying.
- `SECRET_KEY` defaults to a dev value in `security.py` — override it via
  the `SECRET_KEY` environment variable in any real deployment.

## Testing
A good starting point for `backend/tests/test_api.py` using FastAPI's
`TestClient`:
```python
from fastapi.testclient import TestClient
from app import app

def test_health_check():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200

def test_customer_cannot_reach_admin_routes():
    with TestClient(app) as client:
        client.post("/register", json={"name": "T", "email": "t@t.com", "password": "pass123"})
        login = client.post("/login", data={"username": "t@t.com", "password": "pass123"})
        token = login.json()["access_token"]
        response = client.get("/admin/tickets", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
```
Run with `pytest` after adding `pytest` and `httpx` to `requirements.txt`.

## Git Workflow
This repo's history is organized in small, reviewable commits (backend
scaffold → auth → tickets/comments → admin & analytics → frontend →
docs) rather than one large drop, matching how the change would land as
a series of pull requests in a real team.
