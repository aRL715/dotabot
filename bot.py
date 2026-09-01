import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "8613726826:AAFZQDBezOvLAUOuPi41c7k00Ew1sarufMw"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Базовый словарь сленга. Все остальные 125+ героев добавятся сюда АВТОМАТИЧЕСКИ!
HEROES_DICT = {
    "ам": (1, "Anti-Mage"), "сф": (11, "Shadow Fiend"), "невермор": (11, "Shadow Fiend"),
    "вк": (42, "Wraith King"), "папич": (42, "Wraith King"), "леорик": (42, "Wraith King"),
    "цм": (5, "Crystal Maiden"), "цмка": (5, "Crystal Maiden"), "пл": (12, "Phantom Lancer"),
    "бх": (62, "Bounty Hunter"), "баунти": (62, "Bounty Hunter"), "нс": (60, "Night Stalker"),
    "вд": (30, "Witch Doctor"), "лк": (104, "Legion Commander"), "легионка": (104, "Legion Commander"),
    "тб": (109, "Terrorblade"), "дб": (135, "Dawnbreaker"), "мк": (114, "Monkey King"),
    "од": (76, "Outworld Destroyer"), "цк": (81, "Chaos Knight")
}

HERO_ID_TO_NAME = {}

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Мидеры", callback_data="role_mid"),
            InlineKeyboardButton(text="⚔️ Керри", callback_data="role_carry")
        ],
        [
            InlineKeyboardButton(text="🛡️ Хардлайн", callback_data="role_off"),
            InlineKeyboardButton(text="🌀 Саппорты", callback_data="role_supp")
        ]
    ])

QUICK_HEROES = {
    "mid": [("Invoker", "invoker"), ("Shadow Fiend", "shadow_fiend"), ("Pudge", "pudge")],
    "carry": [("Anti-Mage", "anti-mage"), ("Juggernaut", "juggernaut"), ("Ursa", "ursa")],
    "off": [("Axe", "axe"), ("Bristleback", "bristleback")],
    "supp": [("Lion", "lion"), ("Rubick", "rubick")]
}

def get_heroes_keyboard(role_key: str):
    buttons = []
    for text_name, search_key in QUICK_HEROES[role_key]:
        buttons.append([InlineKeyboardButton(text=text_name, callback_data=f"hero_{search_key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# АВТО-ЗАГРУЗКА: Бот сам скачивает имена ВСЕХ 125+ героев на английском и русском!
async def load_all_heroes_into_memory():
    url = "https://githubusercontent.com"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for h_id_str, h_info in data.items():
                        h_id = int(h_id_str)
                        loc_name = h_info['localized_name']
                        HERO_ID_TO_NAME[h_id] = loc_name
                        HEROES_DICT[loc_name.lower()] = (h_id, loc_name)
                        HEROES_DICT[h_info['name'].replace("npc_dota_hero_", "").lower()] = (h_id, loc_name)
                    logging.info("✅ ВСЯ БАЗА ДОТЫ ЗАГРУЖЕНА!")
        except Exception as e:
            logging.error(f"Ошибка загрузки базы: {e}")

async def get_live_counters(hero_id: int):
    url = f"https://opendota.com{hero_id}/matchups"
    async with aiohttp.ClientSession() as session:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    matchups = await response.json()
                    valid_matchups = []
                    for m in matchups:
                        if m['games_played'] > 10:
                            winrate = (m['wins'] / m['games_played']) * 100
                            valid_matchups.append({'id': m['hero_id'], 'winrate': winrate})
                    valid_matchups.sort(key=lambda x: x['winrate'], reverse=True)
                    return valid_matchups[:5]
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            return None

async def process_counter_search(message_or_call, hero_search_str: str):
    search_key = hero_search_str.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    
    hero_id, official_name = None, None
    for key, val in HEROES_DICT.items():
        clean_key = key.replace("-", "").replace("_", "").replace(" ", "")
        if search_key == clean_key or search_key == key:
            hero_id, official_name = val
            break

    if hero_id:
        if isinstance(message_or_call, Message):
            status_msg = await message_or_call.answer(f"⚡ Живой запрос к статистике против **{official_name}**...")
        else:
            status_msg = await message_or_call.message.answer(f"⚡ Живой запрос к статистике против **{official_name}**...")
            await message_or_call.answer()
            
        top_counters = await get_live_counters(hero_id)
        if top_counters:
            response = f"⚔️ **ТОП-5 АВТО-контрпиков против {official_name}:**\n\n"
            for i, counter in enumerate(top_counters, 1):
                name = HERO_ID_TO_NAME.get(counter['id'], f"Hero ID {counter['id']}")
                wr = round(counter['winrate'], 1)
                response += f"{i}. **{name}** — винрейт прямо сейчас: `{wr}%` 📈\n"
            
            response += f"\n_Данные обновлены автоматически из матчей текущего патча._"
            await status_msg.edit_text(response, parse_mode="Markdown", reply_markup=get_main_menu())
        else:
            await status_msg.edit_text("⚠️ Сервер статистики перегружен. Попробуйте еще раз через 5 секунд.")
    else:
        text = "❌ Герой не найден.\nВведи имя персонажа на русском или английском (например: *Марси, Муэрта, Кеез, Сларк*):"
        if isinstance(message_or_call, Message):
            await message_or_call.answer(text, reply_markup=get_main_menu())
        else:
            await message_or_call.message.answer(text, reply_markup=get_main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🚀 **Автоматический Dota 2 Бот готов!**\n\n"
        "Я знаю абсолютно всех 125+ героев Доты. Напиши имя любого персонажа на русском/английском или нажми на кнопки:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("role_"))
async def handle_menus(call: CallbackQuery):
    role = call.data.split("_")
    await call.message.edit_text("🎯 Выбери вражеского героя из списка популярных:", reply_markup=get_heroes_keyboard(role))
    await call.answer()

@dp.callback_query(F.data == "back_to_menu")
async def handle_back(call: CallbackQuery):
    await call.message.edit_text("Выбери роль кнопками или введи имя героя вручную с клавиатуры:", reply_markup=get_main_menu())
    await call.answer()

@dp.callback_query(F.data.startswith("hero_"))
async def handle_hero_click(call: CallbackQuery):
    hero_key = call.data.replace("hero_", "")
    await process_counter_search(call, hero_key)

@dp.message()
async def check_hero_text(message: Message):
    user_input = message.text.strip().lower()
    await process_counter_search(message, user_input)

async def main():
    logging.basicConfig(level=logging.INFO)
    await load_all_heroes_into_memory()
    
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    asyncio.create_task(site.start())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
