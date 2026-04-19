from fastapi import FastAPI

from app.api.routes import router as scaffold_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(scaffold_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
