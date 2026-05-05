import config

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from db import engine, Base
from routes.calls import router as calls_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Prevent browsers and proxies from caching API responses that may contain PII."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response


app = FastAPI(title="Call Review System", lifespan=lifespan)

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls_router, prefix="/api")
