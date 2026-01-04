import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Изменено на DEBUG для подробных логов
)
logger = logging.getLogger(__name__)

# Отключаем избыточные логи от httpx и telegram библиотек
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.INFO)  # Показываем логи telegram
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

def evaluate_artifact(main_stat, sub_stats):
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
        reasons_delete.append("Высокий шанс появления ненужных статов")
    
    # Проверка 2: Основной стат HP Bonus или ATK Bonus
    if main_stat in ["HP Bonus", "ATK Bonus"]:
        reasons_delete.append("Нерелевантный основной стат")
    
    # Проверка 3: Попарно флат статы
    has_hp_atk = "HP" in sub_stats and "ATK" in sub_stats
    has_hp_def = "HP" in sub_stats and "DEF" in sub_stats
    has_atk_def = "ATK" in sub_stats and "DEF" in sub_stats
    
    if has_hp_atk or has_hp_def or has_atk_def:
        reasons_delete.append("2 флат сабстата")
    
    # Проверка 4: 3 стата из комбинаций HP/ATK/DEF (флат или бонус)
    hp_count = int("HP" in sub_stats) + int("HP Bonus" in sub_stats)
    atk_count = int("ATK" in sub_stats) + int("ATK Bonus" in sub_stats)
    def_count = int("DEF" in sub_stats) + int("DEF Bonus" in sub_stats)
    
    categories_with_stats = sum([hp_count > 0, atk_count > 0, def_count > 0])
    if categories_with_stats >= 3:
        reasons_delete.append("3 неподходящих стата")
    
    # Проверка 5: Флат с Oath's Strength
    has_flat = any(stat in sub_stats for stat in flat_stats)
    has_oath = "Oath's Strength" in sub_stats
    if has_flat and has_oath:
        reasons_delete.append("Флат с Oath's Strength")
    
    # Проверка 6: Флат + всего 3 стата
    if has_flat and len(sub_stats) == 3:
        # Проверяем парные бонусы
        has_hp_pair = "HP" in sub_stats and "HP Bonus" in sub_stats
        has_atk_pair = "ATK" in sub_stats and "ATK Bonus" in sub_stats
        has_def_pair = "DEF" in sub_stats and "DEF Bonus" in sub_stats
        
        if has_hp_pair or has_atk_pair or has_def_pair:
            reasons_potentially.append("Хорошее сочетание, но может вылезти ненужный флат или Oath's Strength")
        else:
            reasons_delete.append("Может вылезти флат или Oath's Strength")
    
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
        reasons_delete.append("HP и DEF не сочетаются")
    
    # Проверка 8: CRIT и Weakened
    has_crit = "CRIT Rate" in sub_stats or "CRIT DMG" in sub_stats
    has_weakened = "DMG Boost to Weakened" in sub_stats
    if has_crit and has_weakened:
        reasons_potentially.append("Crit и Weakened лучше разделять по разным протокорам")
    
    # Переопределение: Редкий основной стат
    if is_rare_main and reasons_delete:
        # Переносим все причины удаления в потенциальное удаление
        reasons_potentially.extend(reasons_delete)
        reasons_delete = []
        reasons_potentially.append("Но редкий основной стат - может пригодиться")
    
    # Определяем итоговое решение
    if reasons_delete:
        decision = "❌ Удалить"
    elif reasons_potentially:
        decision = "⚠️ Потенциально удалить"
    else:
        decision = "✅ Сохранить"
    
    return decision, reasons_delete, reasons_potentially

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    user_data[user_id] = {
        'main_stat': None,
        'sub_stats': []
    }
    
    await update.message.reply_text(
        "👋 Привет! Я помогу определить, стоит ли сохранить артефакт.\n\n"
        "Используй /new чтобы начать проверку нового артефакта.\n"
        "Используй /help для получения инструкций."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 Как пользоваться:\n\n"
        "1. Отправь /new чтобы начать\n"
        "2. Выбери основной стат\n"
        "3. Выбери 2-4 дополнительных стата\n"
        "4. Нажми 'Готово' для получения рекомендации\n\n"
        "Команды:\n"
        "/new - начать проверку нового артефакта\n"
        "/cancel - отменить текущий выбор\n"
        "/help - эта справка\n\n"
        "👤 Автор: @Vihanoka\n"
        "По вопросам и комментариям пишите сюда @Vihanoka"
    )

async def new_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать выбор нового артефакта"""
    user_id = update.effective_user.id
    user_data[user_id] = {
        'main_stat': None,
        'sub_stats': []
    }
    
    # Создаем кнопки для выбора основного стата
    keyboard = create_main_stat_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 Выберите основной стат артефакта:",
        reply_markup=reply_markup
    )

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

async def show_new_artifact_menu(query, user_id):
    """Показывает меню для выбора нового артефакта"""
    # Создаем кнопки для выбора основного стата
    keyboard = create_main_stat_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение вместо редактирования старого
    await query.message.reply_text(
        "🎯 Выберите основной стат следующего артефакта:",
        reply_markup=reply_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить текущий выбор"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text(
        "❌ Выбор отменен. Используй /new чтобы начать заново."
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Инициализация данных пользователя, если их нет
    if user_id not in user_data:
        user_data[user_id] = {
            'main_stat': None,
            'sub_stats': []
        }
    
    data = query.data
    
    # Выбор основного стата
    if data.startswith("main_"):
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
        user_data[user_id] = {
            'main_stat': None,
            'sub_stats': []
        }
        await query.edit_message_text("❌ Выбор сброшен. Используй /new чтобы начать заново.")

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
        control_row.append(InlineKeyboardButton("✅ Готово", callback_data="done"))
    control_row.append(InlineKeyboardButton("🔄 Сброс", callback_data="reset"))
    keyboard.append(control_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"⭐ Основной стат: {main_stat}\n\n"
        f"📊 Выберите дополнительные статы ({len(selected_subs)}/4):\n"
    )
    
    if selected_subs:
        text += "\nВыбрано:\n" + "\n".join([f"  • {s}" for s in selected_subs])
    
    text += "\n\n⚠️ Минимум 2, максимум 4 стата"
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def finish_selection(query, user_id):
    """Завершает выбор и выдает рекомендацию"""
    main_stat = user_data[user_id]['main_stat']
    sub_stats = user_data[user_id]['sub_stats']
    
    if len(sub_stats) < 2:
        await query.edit_message_text(
            "❌ Нужно выбрать минимум 2 дополнительных стата.\n"
            "Используй /new чтобы начать заново."
        )
        return
    
    # Оцениваем артефакт
    decision, reasons_delete, reasons_potentially = evaluate_artifact(main_stat, sub_stats)
    
    result_text = (
        f"📋 Результат оценки:\n\n"
        f"⭐ Основной стат: {main_stat}\n"
        f"📊 Дополнительные статы:\n"
    )
    result_text += "\n".join([f"  • {s}" for s in sub_stats])
    result_text += "\n\n"
    
    # Форматируем вывод в зависимости от наличия причин
    if reasons_potentially and reasons_delete:
        # Есть оба типа причин
        result_text += "⚠️ Потенциально удалить:\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_potentially])
        result_text += "\n\n❌ Удалить:\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_delete])
    elif reasons_delete:
        # Только причины для удаления
        result_text += "❌ Удалить:\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_delete])
    elif reasons_potentially:
        # Только причины для потенциального удаления
        result_text += "⚠️ Потенциально удалить:\n"
        result_text += "\n".join([f"  • {r}" for r in reasons_potentially])
    else:
        # Нет причин - сохранить
        result_text += "✅ Сохранить"
    
    await query.edit_message_text(result_text)
    
    # Очищаем данные пользователя и запускаем новую проверку
    user_data[user_id] = {
        'main_stat': None,
        'sub_stats': []
    }
    
    # Автоматически показываем меню для следующего артефакта
    await show_new_artifact_menu(query, user_id)

def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_artifact))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
