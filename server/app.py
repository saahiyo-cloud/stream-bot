import logging
from aiohttp import web
from server.routes import setup_routes

logger = logging.getLogger(__name__)


async def create_web_server() -> web.AppRunner:
    app = web.Application(client_max_size=1024 * 1024 * 10)  # 10 MB request body limit for headers
    setup_routes(app)
    runner = web.AppRunner(app)
    await runner.setup()
    return runner
