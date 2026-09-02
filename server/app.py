import logging
from aiohttp import web
from server.routes import setup_routes

logger = logging.getLogger(__name__)


async def create_web_app() -> web.Application:
    app = web.Application(client_max_size=1024 * 1024 * 10)  # 10 MB request body limit for headers
    setup_routes(app)
    return app


async def create_web_server() -> web.AppRunner:
    app = await create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    return runner
