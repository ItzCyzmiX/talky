from aiohttp import web
from dotenv import load_dotenv
from bot.consts import UPDATES_CHANNEL_ID, BOT_CREATION_CHANNEL

from typing import TYPE_CHECKING

load_dotenv()

if TYPE_CHECKING:
    from bot.bot import Talky


def github_releases_webhook_handler(bot: "Talky"):
    async def _releases_webhook(request: web.Request) -> web.Response:
        event = request.headers.get("X-Github-Event")

        if event == "ping":
            return web.Request(text="pong")

        if event != "release":
            return web.Response(status=401, text="Unsupported Event")

        payload = await request.json()

        if payload["action"] != "created":
            return web.Response(status=401, text="Unsupported Event")

        markdown = payload["release"]["body"]

        bot.version = payload["release"]["tag_name"]

        updates_channel = bot.get_channel(UPDATES_CHANNEL_ID)
        bot_creation_channel = bot.get_channel(BOT_CREATION_CHANNEL)
        await updates_channel.send(
            markdown + f"\n\nTry Talky now in {bot_creation_channel.mention}!"
        )

        return web.Response(status=200)

    return _releases_webhook


async def start_github_webhook(bot: "Talky"):
    app = web.Application()
    app.router.add_post("/github", github_releases_webhook_handler(bot=bot))

    runner = web.AppRunner(app=app)
    await runner.setup()

    site = web.TCPSite(runner=runner, host="0.0.0.0", port=8080)
    await site.start()
