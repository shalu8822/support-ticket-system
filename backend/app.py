import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine, SessionLocal
import models
from security import hash_password
from routers import auth as auth_router
from routers import users as users_router
from routers import tickets as tickets_router
from routers import admin as admin_router

app = FastAPI(
    title="Customer Support Ticket System API",
    description="Role-based (customer / admin) support-ticket platform built with FastAPI + JWT.",
    version="1.0.0",
)

# CORS: in production, replace "*" with your deployed frontend's origin(s).
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(tickets_router.router)
app.include_router(admin_router.router)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def seed_admin():
    """Creates a default admin (support agent) account if none exists yet."""
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.role == models.RoleEnum.admin).first():
            admin = models.User(
                name="Support Admin",
                email="admin@stv.local",
                password=hash_password("Admin@123"),
                role=models.RoleEnum.admin,
            )
            db.add(admin)
            db.commit()
            print("Default admin created -> email: admin@stv.local | password: Admin@123")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_admin()


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "customer-support-ticket-system"}

if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(bind=engine)
    seed_admin()
    uvicorn.run(app, host="127.0.0.1", port=8000)