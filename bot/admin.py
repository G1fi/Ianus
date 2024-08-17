from pathlib import Path

from sqlalchemy import delete
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import ADMINS


class AdminsFilter(filters.UpdateFilter):
    def filter(self, update) -> bool:
        return update.message.from_user.id in ADMINS

ADMINS_FILTER = AdminsFilter()


WAIT, SET_DAY, SET_LECTURE, SET_USER, SET_SUBGROUP = range(5)
GET_VIDEO, GET_MESSAGE, ACCEPT_PING = range(3)


UPLOAD_SETTINGS = {
    'days': None,
    'lectures': None,
    'users': None,
    'subgroup': None
}


CURRENT_MSG = {}


def wipe_upload_settings() -> None:
    global UPLOAD_SETTINGS
    UPLOAD_SETTINGS = {
        'days': None,
        'lectures': None,
        'users': None,
        'subgroup': None
    }


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [{'text': 'Отмена', 'callback_data': 'cancel'}]
        ]
    )


def get_return_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [{'text': 'Вернуться', 'callback_data': 'upload_attendance'}]
        ]
    )


def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [{'text': '📥 Выгрузить посещаемость', 'callback_data': 'first_upload_attendance'}],
            [{'text': '📸 Выгрузить видео-кружок', 'callback_data': 'upload_video'}],
            [{'text': '📢 Запустить рассылку [TODO]', 'callback_data': 'start_ping'}],
            [{'text': '🖊️ Отметить вручную [TODO]', 'callback_data': 'start_ping'}]
        ]
    )


def get_upload_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [{'text': '🌞 Выбрать дни', 'callback_data': 'set_days'}],
            [{'text': '💬 Выбрать пары', 'callback_data': 'set_lectures'}],
            [{'text': '🎓 Выбрать людей', 'callback_data': 'set_users'}],
            [{'text': '💼 Выбрать подгруппу', 'callback_data': 'set_subgroup'}],
            [
                {'text': 'Отмена', 'callback_data': 'cancel'},
                {'text': 'Выгрузить', 'callback_data': 'start_upload_attendance'}
            ]
        ]
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.delete()
    
    await update.message.reply_text(
        f'👨‍💻 Добро пожаловать в админку, {user.first_name}!',
        reply_markup=get_admin_keyboard()
    )

    return ConversationHandler.END


async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    query = update.callback_query
    await query.answer()
    
    CURRENT_MSG[user_id] = await query.edit_message_text(
        '📸 Введите название видео из базы\n'
        'Например: `867536228_16082024_112838.mp4`',
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    
    return GET_VIDEO


async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.delete()
    video_path = Path.cwd() / 'data' / 'proofs' / update.message.text
    
    await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=CURRENT_MSG[user_id].message_id
        )
    
    if not video_path.exists():
        await update.message.reply_text('❌ Видео не найдено')
    else:
        await update.message.reply_video(video_path)
    
    return ConversationHandler.END


def get_text_upload_attendance() -> str:
    text = f'📥 Настройки выгрузки\n\n'
    
    if UPLOAD_SETTINGS['days']:
        text += f'🌞 Дни: {", ".join(["-".join(day) for day in UPLOAD_SETTINGS["days"]])}\n'
    else:
        text += '🌞 Дни: все доступные\n'
        
    if UPLOAD_SETTINGS['lectures']:
        text += f'💬 Пары: {", ".join(UPLOAD_SETTINGS["lectures"])}\n'
    else:
        text += '💬 Пары: все доступные\n'
        
    if UPLOAD_SETTINGS['users']:
        text += f'🎓 Люди: {", ".join(UPLOAD_SETTINGS["users"])}\n'
    else:
        text += '🎓 Люди: все доступные\n'
    if UPLOAD_SETTINGS['subgroup']:
        text += f'💼 Подгруппа: {UPLOAD_SETTINGS["subgroup"]}\n\n'
    else:
        text += '💼 Подгруппа: обе\n\n'
    
    return text + '‼️ Перед выгрузкой проверь настройки ‼️'


async def upload_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'first_upload_attendance':
        wipe_upload_settings()
    
    await query.edit_message_text(
        text=get_text_upload_attendance(),
        reply_markup=get_upload_keyboard()
    )
    
    return WAIT


async def set_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🌞 Укажи промежутки дней в формате\n"
        "дд.мм.гггг-дд.мм.гггг, дд.мм.гггг-дд.мм.гггг...",
        reply_markup=get_return_keyboard()
    )
    
    return SET_DAY


async def get_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    UPLOAD_SETTINGS['days'] = [date.split('-') for date in user_input.split(',')]

    await update.message.delete()
    await update.message.reply_text(
        '🌞 Даты успешно установлены!\n'
        '🚦 Нажми "Вернуться" в предыдущем сообщении',
    )


async def set_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💬 Укажи нужные пары в формате\n"
        "1-4, 7, 8-10",
        reply_markup=get_return_keyboard()
    )
    
    return SET_LECTURE


async def get_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    all_lectures = []
    
    for lectures in user_input.split(','):
        lectures = list(map(int, lectures.split('-')))
        if len(lectures) == 1:
            all_lectures.append(str(lectures[0]))
        if len(lectures) == 2:
            all_lectures.extend(list(map(str, (range(lectures[0], lectures[1]+1)))))
        
    UPLOAD_SETTINGS['lectures'] = all_lectures

    await update.message.delete()
    await update.message.reply_text(
        '💬 Пары успешно установлены!\n'
        '🚦 Нажми "Вернуться" в предыдущем сообщении',
    )


async def set_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎓 Укажи нужных людей в формате:\n"
        "Иванов Иван Иванович, Петров Петр Петрович",
        reply_markup=get_return_keyboard()
    )
    
    return SET_USER


async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    UPLOAD_SETTINGS['users'] = [full_name for full_name in user_input.split(',')]

    await update.message.delete()
    await update.message.reply_text(
        '🎓 Люди успешно установлены!\n'
        '🚦 Нажми "Вернуться" в предыдущем сообщении',
    )
    
    
async def set_subgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💼 Укажи номер основной подгруппы:\n"
        "Просто 1 или 2",
        reply_markup=get_return_keyboard()
    )
    
    return SET_SUBGROUP


async def get_subgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    UPLOAD_SETTINGS['subgroup'] = int(update.message.text)

    await update.message.delete()
    await update.message.reply_text(
        '💼 Номер подгруппы успешно установлен!\n'
        '🚦 Нажми "Вернуться" в предыдущем сообщении',
    )


async def start_upload_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


# TODO
# start_upload_attendance - цсв и джейсона
# пинг всем юзерам
# ВЫГРУЗКУ ЧЕРЕЗ ТРАЙ ЭКСЕПШН? мб и всю настройку выгрузки тоже обернуть?
# ручную отметку

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer('Отменено!')
    
    await query.delete_message()
    return ConversationHandler.END


def handlers() -> list:
    admin_panel_handler = CommandHandler('admin', admin, filters=ADMINS_FILTER)
    
    upload_video_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(upload_video, pattern="^upload_video$")
        ],
        states={
            GET_VIDEO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_video)
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel$'),]
    )
    
    upload_attendance_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(upload_attendance, pattern="^first_upload_attendance$"),
        ],
        states={
            WAIT: [
                CallbackQueryHandler(set_days, pattern="^set_days$"),
                CallbackQueryHandler(set_lectures, pattern="^set_lectures$"),
                CallbackQueryHandler(set_users, pattern="^set_users$"),
                CallbackQueryHandler(set_subgroup, pattern="^set_subgroup$"),
                CallbackQueryHandler(start_upload_attendance, pattern="^start_upload_attendance$")
            ],
            SET_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_days),
            ],
            SET_LECTURE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_lectures),
            ],
            SET_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_users)
            ],
            SET_SUBGROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_subgroup)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(upload_attendance, pattern="^upload_attendance$"),
            CallbackQueryHandler(cancel, pattern='^cancel$')
        ]
    )
    
    return [
        admin_panel_handler,
        upload_video_handler,
        upload_attendance_handler        
    ]

