import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.webhook.aiohttp_handler import SimpleRequestHandler, setup_application

TOKEN = "8613726826:AAFZQDBezOvLAUOuPi41c7k00Ew1sarufMw"
# Официальный веб-адрес твоего сервера на Render (взят из твоих прошлых логов)
WEBHOOK_HOST = "https://onrender.com"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎭 Pudge", callback_data="fast_pudge"),
            InlineKeyboardButton(text="👤 Anti-Mage", callback_data="fast_antimage"),
            InlineKeyboardButton(text="🔥 Invoker", callback_data="fast_invoker")
        ]
    ])

async def find_and_get_counters(message: Message, user_input: str):
    search_name = user_input.strip().lower().replace(" ", "_").replace("-", "")
    status_msg = await message.answer(f"⚡ Авто-запрос к статистике против **{user_input}**...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://opendota.com", headers=headers) as response:
                if response.status != 200:
                    await status_msg.edit_text("⚠️ Ошибка сервера статистики OpenDota. Попробуй позже.")
                    return
                heroes = await response.json()
            
            hero_id = None
            official_name = ""
            
            slang = {
                "сф": "shadow_fiend", "невермор": "shadow_fiend", "пудж": "pudge", "мясник": "pudge",
                "ам": "antimage", "антимаг": "antimage", "вк": "wraith_king", "папич": "wraith_king",
                "леорик": "wraith_king", "инвокер": "invoker", "вокер": "invoker", "акс": "axe",
                "урса": "ursa", "мишка": "ursa", "бара": "spirit_breaker", "баратрум": "spirit_breaker",
                "тракса": "drow_ranger"
            }
            
            if search_name in slang:
                search_name = slang[search_name]

            for hero in heroes:
                sys_name = hero['name'].replace("npc_dota_hero_", "").lower().replace("_", "").replace("-", "")
                loc_name = hero['localized_name'].lower().replace(" ", "").replace("-", "")
                if search_name == sys_name or search_name == loc_name:
                    hero_id = hero['id']
                    official_name = hero['localized_name']
                    break
            
            if not hero_id:
                await status_msg.edit_text("❌ Герой не найден.\nВведи имя на русском или английском (например: *pudge, marci, kez, сф, бара*):")
                return

            url = f"https://opendota.com/{hero_id}/matchups"
            async with session.get(url, headers=headers) as match_response:
                if match_response.status == 200:
                    matchups = await match_response.json()
                    hero_names = {h['id']: h['localized_name'] for h in heroes}
                    
                    valid_matchups = []
                    for m in matchups:
                        if m['games_played'] > 5:
                            winrate = (m['wins'] / m['games_played']) * 100
                            valid_matchups.append({'id': m['hero_id'], 'winrate': winrate})
                    
                    valid_matchups.sort(key=lambda x: x['winrate'], reverse=True)
                    
                    response = f"⚔️ **ТОП-5 АВТО-контрпиков против {official_name}:**\n\n"
                    for i, counter in enumerate(valid_matchups[:5], 1):
                        name = hero_names.get(counter['id'], f"Hero ID {counter['id']}")
                        wr = round(counter['winrate'], 1)
                        response += f"{i}. **{name}** — винрейт прямо сейчас: `{wr}%` 📈\n"
                    
                    response += f"\n_Статистика обновлена автоматически из базы матчей текущего патча._"
                    await status_msg.edit_text(response, parse_mode="Markdown", reply_markup=get_main_menu())
                else:
                    await status_msg.edit_text("⚠️ Не удалось загрузить матчапы персонажа.")
        except Exception as e:
            await status_msg.edit_text("⚠️ Ошибка подключения к сети.")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🚀 **Автоматический Dota 2 Бот готов!**\n\n"
        "Введи имя абсолютно любого героя Доты на русском или английском (например: *Марси, Муэрта, Кеез, Сф, Пудж*), и я выгружу живые контрпики!",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("fast_"))
async def handle_fast_click(call: CallbackQuery):
    hero_name = call.data.replace("fast_", "")
    await call.answer()
    await find_and_get_counters(call.message, hero_name)

@dp.message()
async def check_hero_text(message: Message):
    await find_and_get_counters(message, message.text)

# Логика запуска профессионального вебхука для Render
async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(WEBHOOK_URL)

def main():
    logging.basicConfig(level=logging.INFO)
    dp.startup.register(on_startup)
    
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    # Режим Вебхука автоматически слушает порт 10000, который требует Render
    web.run_app(app, host="0.0.0.0", port=10000)

if __name__ == "__main__":
    main()
