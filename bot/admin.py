import csv, json
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.db_setup import session, and_, or_
from database.models import User, Attendance
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


def get_upload_rows() -> list | str:
    try:
        query = session.query(Attendance).join(User)
        
        if UPLOAD_SETTINGS['days']:
            day_filters = []
            
            for day_group in UPLOAD_SETTINGS['days']:
                day_start = datetime.strptime(day_group[0].strip(), "%d.%m.%Y")
                day_end = day_start
                
                if len(day_group) == 2:
                    day_end = datetime.strptime(day_group[1].strip(), "%d.%m.%Y")
                    
                day_end = day_end.replace(hour=23, minute=59, second=59)
                day_filters.append(Attendance.timestamp.between(day_start, day_end))
                
            query = query.filter(or_(*day_filters))
        
        if UPLOAD_SETTINGS['lectures']:
            query = query.filter(Attendance.lecture_number.in_(UPLOAD_SETTINGS['lectures']))
        
        if UPLOAD_SETTINGS['users']:
            user_filters = []
            
            for user_full_name in UPLOAD_SETTINGS['users']:
                last_name, first_name, middle_name = user_full_name.split()
                user_filters.append(and_(
                    User.last_name == last_name,
                    User.first_name == first_name,
                    User.middle_name == middle_name
                ))
                
            query = query.filter(or_(*user_filters))
        
        if UPLOAD_SETTINGS['subgroup']:
            query = query.filter(User.subgroup == UPLOAD_SETTINGS['subgroup'])
            
            
        return query.order_by(Attendance.timestamp).all()
    
    except Exception as e:
        return repr(e)


def create_simpe_csv_from_rows(rows: list[Attendance]) -> Path:
    date_range = list(set(map(lambda x: x.timestamp.strftime("%d.%m.%Y"), rows)))
    
    header = ['Дата']
    subheader = ['Пара']
    
    for date in date_range:
        header += [date]
        header += [' ' for _ in range(7)]
        
        subheader += [str(i) for i in range(1, 9)]
    
    full_names = set(map(lambda x: f'{x.user.last_name} {x.user.first_name} {x.user.middle_name}', rows))
    full_names = sorted(full_names)
    
    csv_row = {user: ['' for _ in range(len(date_range) * 8)] for user in full_names}
    
    for row in rows:
        csv_row[f'{row.user.last_name} {row.user.first_name} {row.user.middle_name}'] \
        [date_range.index(row.timestamp.strftime("%d.%m.%Y")) * 8 + row.lecture_number - 1] = 1
    
    path = Path.cwd() / 'data' / 'simpe_attendance.csv'

    with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        
        writer.writerow(header)
        writer.writerow(subheader)
        
        for full_name in full_names:
            writer.writerow([full_name] + csv_row[full_name])
            
    return path


def create_extended_csv_from_rows(rows: list[Attendance]) -> Path:
    path = Path.cwd() / 'data' / 'extended_attendance.csv'

    with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(['ID Отметки', 'Telegram ID', 'ФИО', 'Подгруппа', 'Дата', 'Время','Пара', 'Задание', 'Подтверждение'])
        
        for row in rows:
            full_name = f'{row.user.last_name} {row.user.first_name} {row.user.middle_name}'
            user = [row.id, row.user.telegram_id, full_name, row.user.subgroup]
            pare = [row.timestamp.strftime("%d.%m.%Y"), row.timestamp.strftime("%H:%M:%S"), row.lecture_number, row.challenge, row.video_path] 

            writer.writerow(user + pare)

    return path


def create_json_from_rows(rows) -> Path:
    path = Path.cwd() / 'data' / 'extended_attendance.json'

    with open(path, 'w', encoding='utf-8') as jsonfile:
        to_write = {}
        keys = ['Telegram ID', 'ФИО', 'Подгруппа', 'Дата', 'Время', 'Пара', 'Задание', 'Подтверждение']
        
        for row in rows:
            full_name = f'{row.user.last_name} {row.user.first_name} {row.user.middle_name}'
            user = [row.user.telegram_id, full_name, row.user.subgroup]
            pare = [row.timestamp.strftime("%d.%m.%Y"), row.timestamp.strftime("%H:%M:%S"), row.lecture_number, row.challenge, row.video_path] 

            to_write[row.id] = dict(zip(keys, user + pare))
        
        json.dump(to_write, jsonfile, indent=4, ensure_ascii=False)

    return path


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
    
    text += '‼️ Перед выгрузкой проверь настройки ‼️\n'
    
    rows = get_upload_rows()

    if isinstance(rows, str):
        text += f'❌ ОШИБКА: {rows[:100]}... ❌'
    else:
        text += f'🔎 Найдено {len(rows)} записей'
        
    return text


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
    UPLOAD_SETTINGS['days'] = [date.strip().split('-') for date in user_input.split(',')]

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
    callback_query = update.callback_query
    rows = get_upload_rows()
    
    if isinstance(rows, str):
        text = f'Ну ты даун? Ошибка же!'
        await callback_query.answer(text)
        await upload_attendance(update, context)


    text = f'Выгружаю {len(rows)} записей'
    await callback_query.answer(text)
    
    await callback_query.delete_message()
    
    path = create_simpe_csv_from_rows(rows)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=path
    )
    
    path = create_extended_csv_from_rows(rows)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=path
    )
    
    path = create_json_from_rows(rows)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=path
    )

    return ConversationHandler.END

# TODO
# Ручную отметку
# Пинг всем юзерамo

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

