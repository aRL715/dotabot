import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web

TOKEN = "8613726826:AAEZJ0-OknC6NQHyV3O6F2l8yT68l13FEww"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Огромная автономная база лучших контрпиков (Вся Дота в памяти бота!)
COUNTERS_DB = {
    # МИДЕРЫ
    "invoker": ("Invoker", ["Nyx Assassin (Выжигает ману)", "Pugna (Вард на прокаст)", "Templar Assassin", "Broodmother"]),
    "shadow_fiend": ("Shadow Fiend", ["Templar Assassin (Щит от урона)", "Clockwerk (Коги в лицо)", "Storm Spirit", "Zeus"]),
    "pudge": ("Pudge", ["Slardar (Минус броня)", "Ursa (Набивает пассивку)", "Lifestealer (Процентный урон)", "Timbersaw"]),
    "tinker": ("Tinker", ["Clockwerk (Шок мешает лазеру)", "Storm Spirit", "Spectre", "Anti-Mage"]),
    "storm_spirit": ("Storm Spirit", ["Anti-Mage", "Silencer (Глобал сайленс)", "Skywrath Mage", "Doom"]),
    "lina": ("Lina", ["Anti-Mage", "Templar Assassin", "Pugna", "Nyx Assassin"]),
    "zeus": ("Zeus", ["Anti-Mage (Маг. щит)", "Templar Assassin", "Storm Spirit", "Huskar"]),
    "meepo": ("Meepo", ["Axe (Агр на всех клонов)", "Sven (Сплэш)", "Earthshaker (Эхослэм)", "Lich"]),

    # КЕРРИ
    "anti_mage": ("Anti-Mage", ["Phantom Assassin", "Slardar", "Meepo (Сетка ловит блинк)", "Legion Commander", "Axe"]),
    "juggernaut": ("Juggernaut", ["Axe (Агрит сквозь крутилку)", "Slardar", "Windranger", "Outworld Destroyer"]),
    "ursa": ("Ursa", ["Windranger (Убегает)", "Venomancer (Замедляет)", "Shadow Shaman (Контроль)", "Razor"]),
    "kez": ("Kez", ["Axe (Агрит во время комбо)", "Legion Commander (Дуэль)", "Bloodseeker (Раптура)"]),
    "muerta": ("Muerta", ["Phantom Assassin", "Anti-Mage (Маг. защита)", "Juggernaut (Спин сейвит)"]),
    "phantom_assassin": ("Phantom Assassin", ["Axe (Контрит промахи)", "Timbersaw", "Tinker", "Razor (Ворует урон)"]),
    "drow_ranger": ("Drow Ranger", ["Phantom Assassin (Прыжок в лицо)", "Axe", "Clockwerk", "Mars (Арена)"]),
    "wraith_king": ("Wraith King", ["Anti-Mage (Сжигает ману)", "Diffusal Blade (Предмет)", "Lion", "Invoker"]),
    "sniper": ("Sniper", ["Storm Spirit (Прыгает через карту)", "Clockwerk", "Spectre", "Spirit Breaker"]),
    "slark": ("Slark", ["Axe", "Legion Commander", "Bloodseeker (Видит лоу ХП)", "Faceless Void"]),

    # ХАРДЛАЙНЕРЫ
    "axe": ("Axe", ["Viper", "Venomancer", "Necrophos (Ульт в ХП)", "Outworld Destroyer"]),
    "bristleback": ("Bristleback", ["Viper (Выключает спину сломанным пассивом)", "Slark", "Necrophos", "Timbersaw"]),
    "primal_beast": ("Primal Beast", ["Lifestealer", "Slark (Ворует статы)", "Viper", "Bloodseeker"]),
    "slardar": ("Slardar", ["Naga Siren (Иллюзии)", "Phantom Lancer", "Razor", "Underlord"]),
    "timbersaw": ("Timbersaw", ["Viper", "Outworld Destroyer", "Silencer", "Doom"]),
    "legion_commander": ("Legion Commander", ["Linken's Sphere (Предмет)", "Winter Wyvern", "Outworld Destroyer", "Shadow Demon"]),

    # САППОРТЫ
    "lion": ("Lion", ["Rubick", "Silencer", "Lifestealer", "Anti-Mage"]),
    "rubick": ("Rubick", ["Silencer", "Skywrath Mage", "Clinkz", "Riki"]),
    "spirit_breaker": ("Spirit Breaker", ["Underlord", "Clockwerk (Коги стопят разбег)", "Disruptor", "Enigma"]),
    "crystal_maiden": ("Crystal Maiden", ["Silencer", "Clockwerk", "Earthshaker", "Juggernaut"]),
    "witch_doctor": ("Witch Doctor", ["Silencer", "Rubick (Ворует вард)", "Riki", "Bounty Hunter"]),
    "dazzle": ("Dazzle", ["Axe (Топор убивает сквозь крест!)", "Ancient Apparition", "Doom"])
}

# Поддержка ручного ввода на русском языке
RUS_TO_ENG = {
    "пудж": "pudge", "мясник": "pudge", "инвокер": "invoker", "вокер": "invoker", "сф": "shadow_fiend", "невермор": "shadow_fiend",
    "антимаг": "anti_mage", "ам": "anti_mage", "джаггер": "juggernaut", "джаггернаут": "juggernaut", "урса": "ursa", "мишка": "ursa",
    "кеез": "kez", "муэрта": "muerta", "акс": "axe", "брист": "bristleback", "бристлбэк": "bristleback", "ёж": "bristleback",
    "праймал": "primal_beast", "лион": "lion", "рубик": "rubick", "бара": "spirit_breaker", "баратрум": "spirit_breaker",
    "тинкер": "tinker", "шторм": "storm_spirit", "лина": "lina", "зевс": "zeus", "мипо": "meepo", "фантомка": "phantom_assassin",
    "тракса": "drow_ranger", "вк": "wraith_king", "папич": "wraith_king", "снайпер": "sniper", "сларк": "slark", "слардар": "slardar",
    "тимбер": "timbersaw", "легионка": "legion_commander", "цм": "crystal_maiden", "цмка": "crystal_maiden", "вд": "witch_doctor", "дазл": "dazzle"
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
    "mid": [("Invoker", "invoker"), ("Shadow Fiend", "shadow_fiend"), ("Pudge", "pudge"), ("Tinker", "tinker"), ("Storm Spirit", "storm_spirit"), ("Lina", "lina"), ("Zeus", "zeus"), ("Meepo", "meepo")],
    "carry": [("Anti-Mage", "anti_mage"), ("Juggernaut", "juggernaut"), ("Ursa", "ursa"), ("Kez (Кеез)", "kez"), ("Muerta", "muerta"), ("Phantom Assassin", "phantom_assassin"), ("Drow Ranger", "drow_ranger"), ("Wraith King", "wraith_king"), ("Sniper", "sniper"), ("Slark", "slark")],
    "off": [("Axe", "axe"), ("Bristleback", "bristleback"), ("Primal Beast", "primal_beast"), ("Slardar", "slardar"), ("Timbersaw", "timbersaw"), ("Legion Commander", "legion_commander")],
    "supp": [("Lion", "lion"), ("Rubick", "rubick"), ("Spirit Breaker", "spirit_breaker"), ("Crystal Maiden", "crystal_maiden"), ("Witch Doctor", "witch_doctor"), ("Dazzle", "dazzle")]
}

def get_heroes_keyboard(role_key: str):
    buttons = []
    row = []
    for text_name, search_key in QUICK_HEROES[role_key]:
        row.append(InlineKeyboardButton(text=text_name, callback_data=f"hero_{search_key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def process_counter_search(message_or_call, hero_key: str):
    hero_key = hero_key.strip().lower().replace(" ", "_")
    
    if hero_key in RUS_TO_ENG:
        hero_key = RUS_TO_ENG[hero_key]

    if hero_key in COUNTERS_DB:
        official_name, counters = COUNTERS_DB[hero_key]
        response = f"⚔️ **Лучшие контрпики против {official_name}:**\n\n"
        for i, counter in enumerate(counters, 1):
            response += f"{i}. **{counter}**\n"
        response += f"\n_Выбери роль или введи нового героя с клавиатуры:_"
        
        if isinstance(message_or_call, Message):
            await message_or_call.answer(response, parse_mode="Markdown", reply_markup=get_main_menu())
        else:
            await message_or_call.message.edit_text(response, parse_mode="Markdown", reply_markup=get_main_menu())
    else:
        text = "❌ Герой не найден в базе.\nПопробуй выбрать кнопками ролей или введи популярного (например: *Пудж, СФ, Кеез, Акс, Бара, ЦМка*):"
        if isinstance(message_or_call, Message):
            await message_or_call.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())
        else:
            await message_or_call.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "🔮 **Dota 2 Контр-пикер готов к работе!**\n\n"
        "Выбери категорию кнопками ниже или напиши имя вражеского героя с клавиатуры:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data.startswith("role_"))
async def handle_menus(call: CallbackQuery):
    role = call.data.split("_")[1]
    await call.message.edit_text("🎯 Выбери вражеского героя из списка:", reply_markup=get_heroes_keyboard(role))
    await call.answer()

@dp.callback_query(F.data == "back_to_menu")
async def handle_back(call: CallbackQuery):
    await call.message.edit_text("Выбери категорию кнопками ниже или напиши имя вражеского героя с клавиатуры:", reply_markup=get_main_menu())
    await call.answer()

@dp.callback_query(F.data.startswith("hero_"))
async def handle_hero_click(call: CallbackQuery):
    hero_key = call.data.replace("hero_", "")
    await call.answer()
    await process_counter_search(call, hero_key)

@dp.message()
async def check_hero_text(message: Message):
    await process_counter_search(message, message.text)

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
