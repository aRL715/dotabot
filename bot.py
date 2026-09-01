import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web

TOKEN = "8613726826:AAHfoAUUFJV7P-KqxqOu3e3KPgq84pYCrYM"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Наш бронебойный словарь: переводит и сленг, и английские названия популярных кнопок сразу в ID и официальные имена!
HEROES_STATIC_DB = {
    "invoker": (74, "Invoker"), "инвокер": (74, "Invoker"), "вокер": (74, "Invoker"),
    "shadow_fiend": (11, "Shadow Fiend"), "сф": (11, "Shadow Fiend"), "невермор": (11, "Shadow Fiend"),
    "pudge": (14, "Pudge"), "пудж": (14, "Pudge"), "мясник": (14, "Pudge"),
    "anti_mage": (1, "Anti-Mage"), "антимаг": (1, "Anti-Mage"), "ам": (1, "Anti-Mage"),
    "juggernaut": (8, "Juggernaut"), "джаггер": (8, "Juggernaut"), "джаггернаут": (8, "Juggernaut"),
    "ursa": (70, "Ursa"), "урса": (70, "Ursa"), "мишка": (70, "Ursa"),
    "axe": (2, "Axe"), "акс": (2, "Axe"),
    "bristleback": (99, "Bristleback"), "брист": (99, "Bristleback"), "бристлбэк": (99, "Bristleback"), "ёж": (99, "Bristleback"),
    "lion": (26, "Lion"), "лион": (26, "Lion"),
    "rubick": (86, "Rubick"), "рубик": (86, "Rubick"),
    "kez": (145, "Kez"), "кеез": (145, "Kez"),
    "muerta": (138, "Muerta"), "муэрта": (138, "Muerta"),
    "marci": (136, "Marci"), "марси": (136, "Marci"),
    "primal_beast": (137, "Primal Beast"), "праймал": (137, "Primal Beast"), "динозавр": (137, "Primal Beast"),
    "wraith_king": (42, "Wraith King"), "вк": (42, "Wraith King"), "папич": (42, "Wraith King"), "леорик": (42, "Wraith King"),
    "drow_ranger": (6, "Drow Ranger"), "тракса": (6, "Drow Ranger"), "дроу": (6, "Drow Ranger"),
    "sniper": (35, "Sniper"), "снайпер": (35, "Sniper"), "дед": (35, "Sniper"),
    "slark": (93, "Slark"), "сларк": (93, "Slark"), "рыба": (93, "Slark"),
    "spirit_breaker": (71, "Spirit Breaker"), "бара": (71, "Spirit Breaker"), "баратрум": (71, "Spirit Breaker")
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
    "carry": [("Anti-Mage", "anti_mage"), ("Juggernaut", "juggernaut"), ("Ursa", "ursa"), ("Kez (Кеез)", "kez")],
    "off": [("Axe", "axe"), ("Bristleback", "bristleback"), ("Primal Beast", "primal_beast")],
    "supp": [("Lion", "lion"), ("Rubick", "rubick"), ("Spirit Breaker (Бара)", "spirit_breaker")]
}

def get_heroes_keyboard(role_key: str):
    buttons = []
    for text_name, search_key in QUICK_HEROES[role_key]:
        buttons.append([InlineKeyboardButton(text=text_name, callback_data=f"hero_{search_key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_auto_counters(message_or_call, user_input_str: str):
    search_name = user_input_str.strip().lower().replace(" ", "_").replace("-", "")
    
    # Сразу ищем героя и его ID в нашей статической базе
    if search_name in HEROES_STATIC_DB:
        target_id, official_name = HEROES_STATIC_DB[search_name]
    else:
        # Если юзер ввел редкого героя, которого нет в списке популярных — выводим ошибку, бот не зависнет!
        text = "❌ Герой не найден.\nВведи имя популярного персонажа на русском или английском (например: *Марси, Кеез, Сф, Пудж, Тракса, Бара*):"
        if isinstance(message_or_call, Message):
            await message_or_call.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
        else:
            await message_or_call.message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
        return

    # Отправляем сообщение о начале живого поиска
    if isinstance(message_or_call, Message):
        status_msg = await message_or_call.answer(f"⚡ Живой авто-запрос к базе данных против **{official_name}**...")
    else:
        status_msg = await message_or_call.message.answer(f"⚡ Живой авто-запрос к базе данных против **{official_name}**...")
        await message_or_call.answer()

    async with aiohttp.ClientSession() as session:
        try:
            # 1. Скачиваем официальные имена всех героев для красивого вывода результатов
            heroes_url = "https://githubusercontent.com"
            async with session.get(heroes_url) as response:
                if response.status == 200:
                    heroes_data = await response.json()
                    id_to_name = {int(k): v['localized_name'] for k, v in heroes_data.items()}
                else:
                    id_to_name = {}

            # 2. Скачиваем живую матрицу контрпиков (это зеркало Render видит без блокировок!)
            matchups_url = f"https://opendota.com{target_id}/matchups"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            async with session.get(matchups_url, headers=headers) as match_response:
                if match_response.status == 200:
                    matchups = await match_response.json()
                    valid_matchups = []
                    for m in matchups:
                        if m['games_played'] > 10:
                            winrate = (m['wins'] / m['games_played']) * 100
                            valid_matchups.append({'id': int(m['hero_id']), 'winrate': winrate})
                    
                    valid_matchups.sort(key=lambda x: x['winrate'], reverse=True)
                    
                    response = f"⚔️ **ТОП-5 АВТО-контрпиков против {official_name}:**\n\n"
                    for i, counter in enumerate(valid_matchups[:5], 1):
                        name = id_to_name.get(counter['id'], f"Hero ID {counter['id']}")
                        wr = round(counter['winrate'], 1)
                        response += f"{i}. **{name}** — винрейт прямо сейчас: `{wr}%` 📈\n"
                    
                    response += f"\n_Данные обновлены автоматически из базы последних матчей патча._"
                    await status_msg.edit_text(response, parse_mode="Markdown", reply_markup=get_main_menu())
                else:
                    await status_msg.edit_text("⚠️ Ошибка сервера OpenDota. Нажми кнопку еще раз через 5 секунд.", reply_markup=get_main_menu())
        except Exception as e:
            logging.error(f"Ошибка авто-режима: {e}")
            await status_msg.edit_text("⚠️ Ошибка сети при запросе к серверу матчей.", reply_markup=get_main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🚀 **Автоматический Dota 2 Бот готов!**\n\n"
        "Выбери категорию кнопками ниже или напиши имя популярного героя с клавиатуры (на русском/английском):",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("role_"))
async def handle_menus(call: CallbackQuery):
    role = call.data.split("_")[1]
    await call.message.edit_text("🎯 Выбери вражеского героя из списка популярных:", reply_markup=get_heroes_keyboard(role))
    await call.answer()

@dp.callback_query(F.data == "back_to_menu")
async def handle_back(call: CallbackQuery):
    await call.message.edit_text("Выбери роль кнопками или введи имя героя вручную с клавиатуры:", reply_markup=get_main_menu())
    await call.answer()

@dp.callback_query(F.data.startswith("hero_"))
async def handle_hero_click(call: CallbackQuery):
    hero_key = call.data.replace("hero_", "")
    await get_auto_counters(call, hero_key)

@dp.message()
async def check_hero_text(message: Message):
    user_input = message.text.strip().lower()
    await get_auto_counters(message, user_input)

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
