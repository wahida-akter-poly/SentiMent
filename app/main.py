from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse

from app.api.router import router
from app.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import Analysis  # noqa: F401 - registers the model with Base
from app.services.model_adapter import load_model_adapter


class FrontendFiles(StaticFiles):
    """Serve the prototype without exposing backend source or local data."""

    async def get_response(self, path: str, scope):
        blocked = ("app", "tests", "alembic", "artifacts", "data")
        first_segment = path.replace("\\", "/").split("/", 1)[0]
        if first_segment in blocked or path in {".env", ".env.example", "requirements.txt", "alembic.ini"}:
            return PlainTextResponse("Not found", status_code=404)
        return await super().get_response(path, scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.model_adapter = load_model_adapter(get_settings().resolved_model_path)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SENTI-MIND API", version="1.0.0", lifespan=lifespan)
    app.include_router(router)
    frontend = Path(__file__).resolve().parent.parent
    app.mount("/", FrontendFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
