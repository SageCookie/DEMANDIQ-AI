import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config.settings import settings
from src.api.routes import router
from src.utils.logger import logger
from src.database.session import Base, engine
from src.database.session import SessionLocal
from src.database.models import User

# Keep local development convenient while production schema changes remain
# explicitly managed by Alembic.
if settings.app_env == "development":
    Base.metadata.create_all(bind=engine)


def _bootstrap_initial_admin() -> None:
    """Create the first admin on a blank hosted database when explicitly configured."""
    username = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not username or not password:
        return
    from argon2 import PasswordHasher
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "ADMIN").first():
            db.add(User(username=username, password_hash=PasswordHasher().hash(password), role="ADMIN", is_active=True))
            db.commit()
            logger.info("Created configured initial administrator '%s'.", username)
    finally:
        db.close()


_bootstrap_initial_admin()

app = FastAPI(
    title="DemandIQ AI",
    description="AI-Powered Demand Forecasting & Inventory Optimization API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS setup. Credentials and a wildcard origin are incompatible and can expose
# authenticated endpoints to an arbitrary site, so use the explicit allow-list
# in every environment.
_cors_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Exception Handlers for strict API standard response
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    code_map = {
        400: "INVALID_REQUEST",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    code = code_map.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msgs = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_msgs.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(error_msgs)
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing your request. Please try again later."
            }
        }
    )

app.include_router(router)

@app.get("/")
def root():
    return {
        "app": "DemandIQ AI",
        "tagline": "Predict Demand. Optimize Inventory. Decide Smarter.",
        "api_docs": "/docs",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host=settings.host, port=settings.port, reload=True)
