import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web

TOKEN = "8613726826:AAFZQDBEzOvLAUOuPi4lc7k0OeWlsarufMw"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Наш стартовый словарь сленга. Всё остальное подгрузится автоматически!
SLANG_DICT = {
    "ам": "anti_mage", "антимаг": "anti_mage",
    "сф": "shadow_fiend", "невермор": "shadow_fiend",
    "вк": "wraith_king", "папич": "wraith_king", "леорик": "wraith_king",
    "пудж": "pudge", "мясник": "pudge",
    "инвокер": "invoker", "вокер": "invoker",
    "бара": "spirit_breaker", "баратрум": "spirit_breaker",
    "тракса": "drow_ranger", "цм": "crystal_maiden", "цмка": "crystal_maiden"
}

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

# АВТО-ФУНКЦИЯ: Бот лезет в официальный открытый архив Valve и на лету считает лучшие контрпики
async def get_auto_counters(message: Message, user_input: str):
    search_name = user_input.strip().lower().replace(" ", "_").replace("-", "")
    
    # Если юзер ввел сленг — переводим в системное имя
    if search_name in SLANG_DICT:
        search_name = SLANG_DICT[search_name]

    status_msg = await message.answer(f"⚡ Живой авто-запрос к базе данных против **{user_input}**...")

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Скачиваем официальный справочник всех 125+ героев Dota 2
            heroes_url = "https://githubusercontent.com"
            async with session.get(heroes_url) as response:
                if response.status != 200:
                    await status_msg.edit_text("⚠️ Не удалось подключиться к базе Valve. Попробуй позже.")
                    return
                heroes_data = await response.json()

            target_id = None
            official_name = ""

            # Ищем ID введённого героя среди всех существующих в игре
            for h_id_str, h_info in heroes_data.items():
                sys_name = h_info['name'].replace("npc_dota_hero_", "").lower().replace("_", "").replace("-", "")
                loc_name = h_info['localized_name'].lower().replace(" ", "").replace("-", "")
                if search_name == sys_name or search_name == loc_name:
                    target_id = int(h_id_str)
                    official_name = h_info['localized_name']
                    break

            if not target_id:
                await status_msg.edit_text("❌ Герой не найден.\nВведи имя абсолютно любого персонажа на русском или английском (например: *Марси, Муэрта, Кеез, Сларк, Акс*):")
                return

            # 2. Скачиваем живую матрицу контрпиков текущего патча (стабильное зеркало архива матчей)
            matchups_url = f"https://opendota.com{target_id}/matchups"
            # Маскируемся под обычный браузер, чтобы обойти защиту облака Render
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with session.get(matchups_url, headers=headers) as match_response:
                if match_response.status == 200:
                    matchups = await match_response.json()
                    
                    # Создаем карту имён: ID -> Название героя
                    id_to_name = {int(k): v['localized_name'] for k, v in heroes_data.items()}
                    
                    valid_matchups = []
                    for m in matchups:
                        if m['games_played'] > 10:
                            winrate = (m['wins'] / m['games_played']) * 100
                            valid_matchups.append({'id': int(m['hero_id']), 'winrate': winrate})
                    
                    # Сортируем: самый высокий процент побед против врага будет в топе
                    valid_matchups.sort(key=lambda x: x['winrate'], reverse=True)
                    
                    response = f"⚔️ **ТОП-5 АВТО-контрпиков против {official_name}:**\n\n"
                    for i, counter in enumerate(valid_matchups[:5], 1):
                        name = id_to_name.get(counter['id'], f"Hero ID {counter['id']}")
                        wr = round(counter['winrate'], 1)
                        response += f"{i}. **{name}** — винрейт прямо сейчас: `{wr}%` 📈\n"
                    
                    response += f"\n_Данные обновлены автоматически из базы последних матчей текущего патча._"
                    await status_msg.edit_text(response, parse_mode="Markdown", reply_markup=get_main_menu())
                else:
                    await status_msg.edit_text("⚠️ Ошибка сервера статистики OpenDota. Нажми кнопку еще раз через 5 секунд.")
        except Exception as e:
            logging.error(f"Ошибка авто-режима: {e}")
            await status_msg.edit_text("⚠️ Ошибка сети при запросе к архиву матчей.")

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🚀 **Автоматический Dota 2 Бот готов!**\n\n"
        "Я знаю вообще всех 125+ персонажей игры и парсю их винрейты в реальном времени.\n\n"
        "Напиши имя абсолютно ЛЮБОГО героя (на русском или английском) или нажми на кнопки ролей:",
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
    await call.answer()
    await get_auto_counters(call.message, hero_key)

@dp.message()
async def check_hero_text(message: Message):
    await get_auto_counters(message, message.text)

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
