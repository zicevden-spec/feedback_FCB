import logging

from aiohttp import web

from app import db
from app.config import settings

logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-FCB-Token",
}


async def handle_options(request: web.Request):
    return web.Response(headers=CORS_HEADERS)


async def handle_lead(request: web.Request):
    if request.method == "OPTIONS":
        return await handle_options(request)
    token = request.headers.get("X-FCB-Token", "")
    if not settings.WEBHOOK_SECRET or token != settings.WEBHOOK_SECRET:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401, headers=CORS_HEADERS)
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "bad json"}, status=400, headers=CORS_HEADERS)
    ref = str(data.get("ref", "")).strip()
    phone = str(data.get("phone", "")).strip()
    name = str(data.get("name", "")).strip()
    if not ref.isdigit() or not phone:
        return web.json_response({"ok": False, "error": "ref and phone required"}, status=400, headers=CORS_HEADERS)
    ref_id = int(ref)
    db.register_lead(ref_id, phone, name)
    db.log_event(ref_id, name, "Вебхук: регистрация на лендинге", f"телефон: {phone}")
    bot = request.app["bot"]
    try:
        await bot.send_message(
            ref_id,
            f"🎉 По вашей ссылке зарегистрировались!\n\n👤 {name or 'Имя не указано'}\n📞 {phone}\n\nСтатус реферала: зарегистрирован на лендинге.",
        )
    except Exception as e:
        logger.error("Не удалось уведомить реферера %s: %s", ref_id, e)
    return web.json_response({"ok": True}, headers=CORS_HEADERS)


async def start(bot):
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/api/lead", handle_lead)
    app.router.add_options("/api/lead", handle_options)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.WEB_PORT)
    await site.start()
    logger.info("Вебхук-API поднято на порту %s", settings.WEB_PORT)
