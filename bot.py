import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Твой токен от BotFather
TOKEN = "8613726826:AAFZQDBEzOvLAUOuPi4lc7k0OeWlsarufMw"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кнопки для быстрого теста популярных героев
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎭 Pudge", callback_data="fast_pudge"),
            InlineKeyboardButton(text="👤 Anti-Mage", callback_data="fast_antimage"),
            InlineKeyboardButton(text="🔥 Invoker", callback_data="fast_invoker")
        ]
    ])

# Функция автоматического поиска ID героя по его названию в системе OpenDota
async def find_hero_id_and_counters(message: Message, hero_name_input: str):
    # Приводим к системному виду (заменяем пробелы на подчеркивания, как в Доте)
    search_name = hero_name_input.strip().lower().replace(" ", "_")
    
    status_msg = await message.answer(f"⚡ Живой запрос к OpenDota API против **{hero_name_input}**...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Сначала автоматически ищем внутренний ID героя по его имени
            async with session.get("https://opendota.com") as response:
                if response.status != 200:
                    await status_msg.edit_text("⚠️ Ошибка сервера OpenDota. Попробуй позже.")
                    return
                
                heroes = await response.json()
                hero_id = None
                official_name = ""
                
                for hero in heroes:
                    # Проверяем совпадение по системному имени или красивому локализованному
                    if search_name in hero['name'].replace("npc_dota_hero_", "") or search_name == hero['localized_name'].lower():
                        hero_id = hero['id']
                        official_name = hero['localized_name']
                        break
                
                if not hero_id:
                    await status_msg.edit_text("❌ Герой не найден.\nВведи точное имя на английском (например: *pudge, marci, muerta, kez*):")
                    return

            # Теперь автоматически запрашиваем живые контрпики по найденному ID
            async with session.get(f"https://opendota.com/{hero_id}/matchups") as match_response:
                if match_response.status == 200:
                    matchups = await match_response.json()
                    
                    # Создаем справочник имен для вывода контрпиков
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
                    await status_msg.edit_text("⚠️ Не удалось получить матчапы.")
        except Exception as e:
            logging.error(f"Ошибка сети: {e}")
            await status_msg.edit_text("⚠️ Ошибка подключения. Убедись, что твой VPN включен!")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🚀 **Полностью автоматический Dota 2 Бот готов!**\n\n"
        "Тебе больше не нужны базы данных. Напиши имя абсолютно **любого героя на английском** "
        "(например: *marci, muerta, kez, slark, sniper*), и я сам найду его ID и спаршу живые контрпики!",
        reply_markup=get_main_menu()
    )

# Обработка быстрых тестовых кнопок
@dp.callback_query(F.data.startswith("fast_"))
async def handle_fast_click(call: CallbackQuery):
    hero_name = call.data.replace("fast_", "")
    await call.answer()
    await find_hero_id_and_counters(call.message, hero_name)

# Обработка ручного ввода имени героя с клавиатуры
@dp.message()
async def check_hero_text(message: Message):
    await find_hero_id_and_counters(message, message.text)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Создаем встроенный веб-сервер, чтобы Render видел открытый порт
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    asyncio.create_task(site.start())
    
    # Запускаем чтение сообщений из Телеграма
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
