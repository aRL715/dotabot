import logging
import asyncio
import aiohttp
from aiohttp import ClientSession, web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "8613726826:AAFZQDBEzOvLAUOuPi4lc7k0OeWlsarufMw"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎭 Pudge", callback_data="fast_pudge"),
            InlineKeyboardButton(text="👤 Anti-Mage", callback_data="fast_antimage"),
            InlineKeyboardButton(text="🔥 Invoker", callback_data="fast_invoker")
        ]
    ])

# Единая надежная функция авто-поиска контрпиков по локальной базе данных матчей
async def find_and_get_counters(message: Message, user_input: str):
    search_name = user_input.strip().lower().replace(" ", "_").replace("-", "")
    status_msg = await message.answer(f"⚡ Авто-запрос к статистике против **{user_input}**...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with ClientSession(headers=headers) as session:
        try:
            # Используем стабильное официальное хранилище Valve для поиска ID всех 125+ героев
            async with session.get("https://githubusercontent.com") as response:
                if response.status != 200:
                    await status_msg.edit_text("⚠️ Ошибка сервера Valve. Попробуй позже.")
                    return
                heroes_data = await response.json()
            
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

            for h_id_str, h_info in heroes_data.items():
                sys_name = h_info['name'].replace("npc_dota_hero_", "").lower().replace("_", "").replace("-", "")
                loc_name = h_info['localized_name'].lower().replace(" ", "").replace("-", "")
                if search_name == sys_name or search_name == loc_name:
                    hero_id = int(h_id_str)
                    official_name = h_info['localized_name']
                    break
            
            if not hero_id:
                await status_msg.edit_text("❌ Герой не найден.\nВведи имя на русском или английском (например: *pudge, marci, kez, сф, бара*):")
                return

            # Запрашиваем живые матчапы текущего патча
            url = f"https://opendota.com{hero_id}/matchups"
            async with session.get(url) as match_response:
                if match_response.status == 200:
                    matchups = await match_response.json()
                    hero_names = {int(k): v['localized_name'] for k, v in heroes_data.items()}
                    
                    valid_matchups = []
                    for m in matchups:
                        if m['games_played'] > 5:
                            winrate = (m['wins'] / m['games_played']) * 100
                            valid_matchups.append({'id': int(m['hero_id']), 'winrate': winrate})
                    
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
            logging.error(f"Критическая ошибка: {e}")
            await status_msg.edit_text("⚠️ Ошибка подключения к серверу статистики.")

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

async def start_bot():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_bot())
