import asyncio
import logging

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sse_starlette import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

_log = logging.getLogger(__name__)
log_fmt = r"%(asctime)-15s %(levelname)s %(name)s %(funcName)s:%(lineno)d %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(format=log_fmt, level=logging.DEBUG, datefmt=datefmt)


@pytest.fixture
def anyio_backend():
    """Exclude trio from tests"""
    return "asyncio"


@pytest.fixture
async def app():
    async def startup():
        print("Starting up")

    async def shutdown():
        print("Shutting down")

    async def home(request):
        return PlainTextResponse("Hello, world!")

    async def endless(req: Request):
        async def event_publisher():
            i = 0
            try:
                while True:  # i <= 20:
                    # yield dict(id=..., event=..., data=...)
                    i += 1
                    yield dict(data=i)
                    await asyncio.sleep(0.3)
            except asyncio.CancelledError as e:
                _log.info(f"Disconnected from client (via refresh/close) {req.client}")
                # Do any other cleanup, if any
                raise e

        return EventSourceResponse(event_publisher())

    app = Starlette(
        routes=[Route("/", home), Route("/endless", endpoint=endless)],
        on_startup=[startup],
        on_shutdown=[shutdown],
    )

    async with LifespanManager(app):
        print("We're in!")
        yield app


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(app=app, base_url="http://localhost:8000") as client:
        print("Yielding Client")
        yield client
