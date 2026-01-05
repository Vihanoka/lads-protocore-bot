import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отключаем избыточные логи от httpx и telegram библиотек
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('telegram.ext').setLevel(logging.INFO)

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Возможные значения статов
MAIN_STATS = [
    "HP", "HP Bonus", "ATK", "ATK Bonus", "DEF Bonus",
    "CRIT Rate", "CRIT DMG", "Expedited Energy Boost",
    "Oath Recovery Boost", "Oath's Strength", "DMG Boost to Weakened"
]

SUB_STATS = [
    "HP", "HP Bonus", "ATK", "ATK Bonus", "DEF", "DEF Bonus",
    "CRIT Rate", "CRIT DMG", "Oath's Strength", "DMG Boost to Weakened"
]

# Временное хранилище данных пользователей
user_data = {}

# Словарь переводов
TRANSLATIONS = {
    'ru': {
        'choose_language': '🌍 Выберите язык / Choose language:',
        'language_set': '✅ Язык установлен: Русский',
        'start_message': '👋 Привет! Я помогу определить, стоит ли сохранить протокор.\n\nИспользуй /new чтобы начать проверку нового протокора.\nИспользуй /help для получения инструкций.\nИспользуй /language для смены языка.',
        'help_title': '📖 Как пользоваться:\n\n',
        'help_steps': '1. Отправь /new чтобы начать\n2. Выбери основной стат\n3. Выбери 2-4 дополнительных стата\n4. Нажми \'Готово\' для получения рекомендации\n\n',
        'help_commands': 'Команды:\n/new - начать проверку нового протокора\n/cancel - отменить текущий выбор\n/language - сменить язык\n/help - эта справка\n\n',
        'help_author': '👤 По вопросам и комментариям пишите сюда @Vihanoka',
        'choose_main_stat': '🎯 Выберите основной стат протокора:',
        'choose_next_main_stat': '🎯 Выберите основной стат следующего протокора:',
        'main_stat': '⭐ Основной стат',
        'choose_sub_stats': '📊 Выберите дополнительные статы',
        'selected': 'Выбрано',
        'min_warning': '⚠️ Минимум 2, максимум 4 стата',
        'sub_stats_list': '\nВыбрано:\n',
        'button_done': '✅ Готово',
        'button_reset': '🔄 Сброс',
        'min_stats_error': '❌ Нужно выбрать минимум 2 дополнительных стата.\nИспользуй /new чтобы начать заново.',
        'result_title': '📋 Результат оценки:\n\n',
        'sub_stats_title': '📊 Дополнительные статы:\n',
        'cancel_message': '❌ Выбор отменен. Используй /new чтобы начать заново.',
        'decision_keep': '✅ Сохранить',
        'decision_delete': '❌ Удалить',
        'decision_maybe': '⚠️ Потенциально удалить',
        'reason_low_substats': 'Высокий шанс появления ненужных статов',
        'reason_bad_main': 'Нерелевантный основной стат',
        'reason_two_flats': '2 флат сабстата',
        'reason_three_bad': '3 неподходящих стата',
        'reason_flat_oath': 'Флат с Oath\'s Strength',
        'reason_good_but_risky': 'Хорошее сочетание, но может вылезти ненужный флат или Oath\'s Strength',
        'reason_may_get_bad': 'Может вылезти флат или Oath\'s Strength',
        'reason_hp_def': 'HP и DEF не сочетаются',
        'reason_crit_weakened': 'Crit и Weakened лучше разделять по разным протокорам',
        'reason_rare_main': 'Но редкий основной стат - может пригодиться',
    },
    'en': {
        'choose_language': '🌍 Choose language / Выберите язык:',
        'language_set': '✅ Language set to: English',
        'start_message': '👋 Hello! I will help you determine whether to keep a protocore.\n\nUse /new to start checking a new protocore.\nUse /help for instructions.\nUse /language to change language.',
        'help_title': '📖 How to use:\n\n',
        'help_steps': '1. Send /new to start\n2. Choose main stat\n3. Choose 2-4 substats\n4. Press \'Done\' to get recommendation\n\n',
        'help_commands': 'Commands:\n/new - start checking new protocore\n/cancel - cancel current selection\n/language - change language\n/help - this help\n\n',
        'help_author': '👤 Author: @Vihanoka\nFor questions and comments contact @Vihanoka',
        'choose_main_stat': '🎯 Choose protocore main stat:',
        'choose_next_main_stat': '🎯 Choose next protocore main stat:',
        'main_stat': '⭐ Main stat',
        'choose_sub_stats': '📊 Choose substats',
        'selected': 'Selected',
        'min_warning': '⚠️ Minimum 2, maximum 4 stats',
        'sub_stats_list': '\nSelected:\n',
        'button_done': '✅ Done',
        'button_reset': '🔄 Reset',
        'min_stats_error': '❌ You need to select at least 2 substats.\nUse /new to start again.',
        'result_title': '📋 Evaluation result:\n\n',
        'sub_stats_title': '📊 Substats:\n',
        'cancel_message': '❌ Selection cancelled. Use /new to start again.',
        'decision_keep': '✅ Keep',
        'decision_delete': '❌ Delete',
        'decision_maybe': '⚠️ Potentially delete',
        'reason_low_substats': 'High chance of getting unwanted stats',
        'reason_bad_main': 'Irrelevant main stat',
        'reason_two_flats': '2 flat substats',
        'reason_three_bad': '3 unsuitable stats',
        'reason_flat_oath': 'Flat with Oath\'s Strength',
        'reason_good_but_risky': 'Good combination, but may roll unwanted flat or Oath\'s Strength',
        'reason_may_get_bad': 'May roll flat or Oath\'s Strength',
        'reason_hp_def': 'HP and DEF don\'t synergize',
        'reason_crit_weakened': 'Crit and Weakened better separated on different protocores',
        'reason_rare_main': 'But rare main stat - might be useful',
    }
}

def get_text(user_id, key):
    """Получить текст на языке пользователя"""
    lang = user_data.get(user_id, {}).get('language', 'en')
    return TRANSLATIONS[lang].get(key, key)

def evaluate_artifact(main_stat, sub_stats, user_id):
    """
    Оценивает артефакт на основе комбинации статов
    Возвращает: (решение, список причин для удаления, список причин для потенциального удаления)
    """
    reasons_delete = []
    reasons_potentially = []
    
    # Редкие основные статы
    rare_main_stats = ["Expedited Energy Boost", "Oath Recovery Boost", "Oath's Strength"]
    is_rare_main = main_stat in rare_main_stats
    
    # Флат статы
    flat_stats = ["HP", "ATK", "DEF"]
    
    # Проверка 1: Меньше 2 сабстатов
    if len(sub_stats) < 2:
        reasons_delete.append(get_text(user_id, 'reason_low_substats'))
    
    # Проверка 2: Основной стат HP Bonus или ATK Bonus
    if main_stat in ["HP Bonus", "ATK Bonus"]:
        reasons_delete.append(get_text(user_id, 'reason_bad_main'))
    
    # Проверка 3: Попарно флат статы
    has_hp_atk = "HP" in sub_stats and "ATK" in sub_stats
    has_hp_def = "HP" in sub_stats and "DEF" in sub_stats
    has_atk_def = "ATK" in sub_stats and "DEF" in sub_stats
    
    if has_hp_atk or has_hp_def or has_atk_def:
        reasons_delete.append(get_text(user_id, 'reason_two_flats'))
    
    # Проверка 4: 3 стата из комбинаций HP/ATK/DEF (флат или бонус)
    hp_count = int("HP" in sub_stats) + int("HP Bonus" in sub_stats)
    atk_count = int("ATK" in sub_stats) + int("ATK Bonus" in sub_stats)
    def_count = int("DEF" in sub_stats) + int("DEF Bonus" in sub_stats)
    
    categories_with_stats = sum([hp_count > 0, atk_count > 0, def_count > 0])
    if categories_with_stats >= 3:
        reasons_delete.append(get_text(user_id, 'reason_three_bad'))
    
    # Проверка 5: Флат с Oath's Strength
    has_flat = any(stat in sub_stats for stat in flat_stats)
    has_oath = "Oath's Strength" in sub_stats
    if has_flat and has_oath:
        reasons_delete.append(get_text(user_id, 'reason_flat_oath'))
    
    # Проверка 6: Флат + всего 3 стата
    if has_flat and len(sub_stats) == 3:
        # Проверяем парные бонусы
        has_hp_pair = "HP" in sub_stats and "HP Bonus" in sub_stats
        has_atk_pair = "ATK" in sub_stats and "ATK Bonus" in sub_stats
        has_def_pair = "DEF" in sub_stats and "DEF Bonus" in sub_stats
        
        if has_hp_pair or has_atk_pair or has_def_pair:
            reasons_potentially.append(get_text(user_id, 'reason_good_but_risky'))
        else:
            reasons_delete.append(get_text(user_id, 'reason_may_get_bad'))
    
    # Проверка 7: HP и DEF не сочетаются
    hp_def_combinations = [
        ("HP" in sub_stats and "DEF" in sub_stats),
        ("HP Bonus" in sub_stats and "DEF Bonus" in sub_stats),
        ("HP" in sub_stats and "DEF Bonus" in sub_stats),
        ("HP Bonus" in sub_stats and "DEF" in sub_stats),
        # Основной стат + сабстаты
        (main_stat in ["HP", "HP Bonus"] and ("DEF" in sub_stats or "DEF Bonus" in sub_stats)),
        (main_stat in ["DEF", "DEF Bonus"] and ("HP" in sub_stats or "HP Bonus" in sub_stats))
    ]
    
    if any(hp_def_combinations):
        reasons_delete.append(get_text(user_id, 'reason_hp_def'))
    
    # Проверка 8: CRIT и Weakened
    has_crit = "CRIT Rate" in sub_stats or "CRIT DMG" in sub_stats
    has_weakened = "DMG Boost to Weakened" in sub_stats
    if has_crit and has_weakened:
        reasons_potentially.append(get_text(user_id, 'reason_crit_weakened'))
    
    # Переопределение: Редкий основной стат
    if is_rare_main and reasons_delete:
        # Переносим все причины удаления в потенциальное удаление
        reasons_potentially.extend(reasons_delete)
        reasons_delete = []
        reasons_potentially.append(get_text(user_id, 'reason_rare_main'))
    
    return reasons_delete, reasons_potentially

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать выбор языка"""
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            TRANSLATIONS['en']['choose_language'],
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.message.reply_text(
            TRANSLATIONS['en']['choose_language'],
            reply_markup=reply_markup
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    
    # Если язык уже выбран, показываем стартовое сообщение
    if user_id in user_data and 'language' in user_data[user_id]:
        user_data[user_id] = {
            'language': user_data[user_id]['language'],
            'main_stat': None,
            'sub_stats': []
        }
        await update.message.reply_text(get_text(user_id, 'start_message'))
    else:
        # Первый запуск - показываем выбор языка
        user_data[user_id] = {
            'language': None,
            'main_stat': None,
            'sub_stats': []
        }
        await choose_language(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        get_text(user_id, 'help_title') +
        get_text(user_id, 'help_steps') +
        get_text(user_id, 'help_commands') +
        get_text(user_id, 'help_author')
    )

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /language"""
    await choose_language(update, context)

async def new_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать выбор нового артефакта"""
    user_id = update.effective_user.id
    
    # Если язык не выбран, показываем выбор языка
    if user_id not in user_data or 'language' not in user_data[user_id]:
        await choose_language(update, context)
        return
    
    user_data[user_id]['main_stat'] = None
    user_data[user_id]['sub_stats'] = []
    
    # Создаем кнопки для выбора основного стата
    keyboard = create_main_stat_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text(user_id, 'choose_main_stat'),
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить текущий выбор"""
    user_id = update.effective_user.id
    if user_id in user_data:
        lang = user_data[user_id].get('language')
        user_data[user_id] = {
            'language': lang,
            'main_stat': None,
            'sub_stats': []
        }
    
    await update.message.reply_text(get_text(user_id, 'cancel_message'))

def create_main_stat_keyboard():
    """Создаёт клавиатуру для выбора основного стата"""
    keyboard = []
    for i in range(0, len(MAIN_STATS), 2):
        row = []
        row.append(InlineKeyboardButton(MAIN_STATS[i], callback_data=f"main_{MAIN_STATS[i]}"))
        if i + 1 < len(MAIN_STATS):
            row.append(InlineKeyboardButton(MAIN_STATS[i + 1], callback_data=f"main_{MAIN_STATS[i + 1]}"))
        keyboard.append(row)
    return keyboard

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Инициализация данных пользователя, если их нет
    if user_id not in user_data:
        user_data[user_id] = {
            'language': None,
            'main_stat': None,
            'sub_stats': []
        }
    
    data = query.data
    
    # Выбор языка
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        user_data[user_id]['language'] = lang
        await query.edit_message_text(TRANSLATIONS[lang]['language_set'])
        await query.message.reply_text(get_text(user_id, 'start_message'))
    
    # Выбор основного стата
    elif data.startswith("main_"):
        stat = data.replace("main_", "")
        user_data[user_id]['main_stat'] = stat
        
        # Показываем выбор дополнительных статов
        await show_sub_stats_menu(query, user_id)
    
    # Выбор/отмена дополнительного стата
    elif data.startswith("sub_"):
        stat = data.replace("sub_", "")
        
        if stat in user_data[user_id]['sub_stats']:
            # Если стат уже выбран, убираем его
            user_data[user_id]['sub_stats'].remove(stat)
        else:
            # Если не выбран, добавляем (максимум 4)
            if len(user_data[user_id]['sub_stats']) < 4:
                user_data[user_id]['sub_stats'].append(stat)
        
        # Обновляем меню
        await show_sub_stats_menu(query, user_id)
    
    # Завершение выбора
    elif data == "done":
        await finish_selection(query, user_id)
    
    # Сброс выбора
    elif data == "reset":
        lang = user_data[user_id].get('language')
        user_data[user_id] = {
            'language': lang,
            'main_stat': None,
            'sub_stats': []
        }
        await query.edit_message_text(get_text(user_id, 'cancel_message'))

async def show_sub_stats_menu(query, user_id):
    """Показывает меню выбора дополнительных статов"""
    main_stat = user_data[user_id]['main_stat']
    selected_subs = user_data[user_id]['sub_stats']
    
    # Создаем кнопки для дополнительных статов
    keyboard = []
    for i in range(0, len(SUB_STATS), 2):
        row = []
        
        stat1 = SUB_STATS[i]
        # Помечаем выбранные статы галочкой
        label1 = f"✓ {stat1}" if stat1 in selected_subs else stat1
        row.append(InlineKeyboardButton(label1, callback_data=f"sub_{stat1}"))
        
        if i + 1 < len(SUB_STATS):
            stat2 = SUB_STATS[i + 1]
            label2 = f"✓ {stat2}" if stat2 in selected_subs else stat2
            row.append(InlineKeyboardButton(label2, callback_data=f"sub_{stat2}"))
        
        keyboard.append(row)
    
    # Кнопки управления
    control_row = []
    if len(selected_subs) >= 2:
        control_row.append(InlineKeyboardButton(
            get_text(user_id, 'button_done'),
            callback_data="done"
        ))
    control_row.append(InlineKeyboardButton(
        get_text(user_id, 'button_reset'),
        callback_data="reset"
    ))
    keyboard.append(control_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"{get_text(user_id, 'main_stat')}: {main_stat}\n\n"
        f"{get_text(user_id, 'choose_sub_stats')} ({len(selected_subs)}/4):\n"
    )
    
    if selected_subs:
        text += get_text(user_id, 'sub_stats_list') + "\n".join([f"  • {s}" for s in selected_subs])
    
    text += "\n\n" + get_text(user_id, 'min_warning')
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def finish_selection(query, user_id):
    """Завершает выбор и выдает рекомендацию"""
    main_stat = user_data[user_id]['main_stat']
    sub_stats = user_data[user_id]['sub_stats']
    
    if len(sub_stats) < 2:
        await query.edit_message_text(get_text(user_id, 'min_stats_error'))
        return
    
    # Оцениваем артефакт
    reasons_delete, reasons_potentially = evaluate_artifact(main_stat, sub_stats, user_id)
    
    result_text = (
        get_text(user_id, 'result_title') +
        f"{get_text(user_id, 'main_stat')}: {main_stat}\n" +
        get_text(user_id, 'sub_stats_title')
    )
    result_text += "\n".join([f"  • {s}" for s in sub_stats])
    result_text += "\n\n"
    
    # Форматируем вывод в зависимости от наличия причин
    if reasons_potentially and reasons_delete:
        # Есть оба типа причин
        result_text += get_text(user_id, 'decision_maybe') + ":\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_potentially])
        result_text += "\n\n" + get_text(user_id, 'decision_delete') + ":\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_delete])
    elif reasons_delete:
        # Только причины для удаления
        result_text += get_text(user_id, 'decision_delete') + ":\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_delete])
    elif reasons_potentially:
        # Только причины для потенциального удаления
        result_text += get_text(user_id, 'decision_maybe') + ":\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_potentially])
    else:
        # Нет причин - сохранить
        result_text += get_text(user_id, 'decision_keep')
    
    await query.edit_message_text(result_text)
    
    # Очищаем данные пользователя и запускаем новую проверку
    lang = user_data[user_id]['language']
    user_data[user_id] = {
        'language': lang,
        'main_stat': None,
        'sub_stats': []
    }
    
    # Автоматически показываем меню для следующего артефакта
    await show_new_artifact_menu(query, user_id)

async def show_new_artifact_menu(query, user_id):
    """Показывает меню для выбора нового артефакта"""
    # Создаем кнопки для выбора основного стата
    keyboard = create_main_stat_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение вместо редактирования старого
    await query.message.reply_text(
        get_text(user_id, 'choose_next_main_stat'),
        reply_markup=reply_markup
    )

def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("new", new_artifact))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
