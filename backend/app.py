import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from streamlit import status
from sqlalchemy import text
from logging_config import logger,setup_logging
#from exceptions import register_exception_handlers
from middleware import RequestLoggingMiddleware

from database import Base, engine, SessionLocal
import models
from security import hash_password
from routers import auth as auth_router
from routers import users as users_router
from routers import tickets as tickets_router
from routers import admin as admin_router

# Initialize professional logging
setup_logging()
#logger = logging.getLogger(__name__)
app = FastAPI(
    title="Customer Support Ticket System API",
    description="Role-based (customer / admin) support-ticket platform built with FastAPI + JWT.",
    version="1.0.0",
)

#register_exception_handlers(app)

# Add our Middleware
app.add_middleware(RequestLoggingMiddleware)

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

# UPGRADE: Global Exception Handler (The Safety Net)
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     request_id = request.headers.get("X-Request-ID", "N/A")
    
#     # Log the full error internally
#     logger.error(
#         f"Unhandled exception occurred: {str(exc)}", 
#         extra={"request_id": request_id}, 
#         exc_info=True
#     )
    
#     # Return a clean, professional error to the client
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # type: ignore
#         content={
#             "error_code": "INTERNAL_SERVER_ERROR",
#             "message": "An unexpected error occurred. Please contact support.",
#             "request_id": request_id  # The user can give this ID to the admin
#         }
#     )

@app.get("/debug-crash")
def crash_me():
    return 1 / 0  # This will trigger a ZeroDivisionError

@app.on_event("startup")
def on_startup():
    #run_migrations()
    seed_admin()
    logger.info("Application startup complete")


@app.get("/", tags=["Health"])
def health_check():
    """Liveness check — always returns ok if the process can respond at all."""
    return {"status": "ok", "service": "customer-support-ticket-system"}


@app.get("/health", tags=["Health"])
def deep_health_check():
    """
    Readiness check: actually pings the database instead of just returning
    a static "ok". If the DB connection is down, this reports it -- so a
    load balancer or on-call engineer finds out before a customer does.
    """
    checks = {"api": "ok", "database": "unknown"}
    db_latency_ms = None
    overall_status = "ok"

    db = SessionLocal()
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "unreachable"
        overall_status = "degraded"
        logger.error("Database health check failed", extra={"error": str(exc)})
    finally:
        db.close()

    return {
        "status": overall_status,
        "checks": checks,
        "database_latency_ms": db_latency_ms,
    }


if __name__ == "__main__":
    import uvicorn
    Base.metadata.create_all(bind=engine)
    seed_admin()
    uvicorn.run(app, host="127.0.0.1", port=8000)