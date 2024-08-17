from pathlib import Path
from random import choice

from sqlalchemy import TEXT
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import CHALLENGES
from database.db_setup import session
from database.models import Attendance, User
from .captcha import generate_captcha, get_lecture_number, get_current_time


CAPTCHA, CHALLENGE = range(2)

CAPTCHA_SOLUTIONS = {}
CAPTCHA_MESSAGES = {}

CHALLENGE_SOLUTIONS = {}
CHALLENGE_MESSAGES = {}


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [{'text': 'Отмена', 'callback_data': 'cancel'}]
        ]
    )


async def attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    
    user_id = update.message.from_user.id
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text('❌ Сначала зарегистрируйся - /reg')
        return ConversationHandler.END

    if not get_lecture_number(get_current_time()):
        await update.message.reply_text('💤 Бро, ты время видел? Какие пары...')
        return ConversationHandler.END

    captcha_image, captcha_solution = generate_captcha()
    CAPTCHA_SOLUTIONS[user_id] = captcha_solution

    CAPTCHA_MESSAGES[user_id] = await update.message.reply_photo(
        photo=captcha_image,
        caption=(
            '🤖 Введи текст с изображения, чтобы отметиться.'
        ),
        reply_markup=get_cancel_keyboard()
    )
    
    return CAPTCHA


async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    
    user_id = update.message.from_user.id
    user_input = update.message.text
    
    await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=CAPTCHA_MESSAGES[user_id].message_id
        )
    # del CAPTCHA_MESSAGES[user_id]

    if user_input.upper() == CAPTCHA_SOLUTIONS.get(user_id):
        challenge_text = (
            f'*{choice(CHALLENGES[0])}* и скажи '
            f'*"{choice(CHALLENGES[1])}"* на камеру'
        )
        
        CHALLENGE_SOLUTIONS[user_id] = challenge_text
        CHALLENGE_MESSAGES[user_id] = await update.message.reply_text(
            f'Чтобы отметиться отправь видео-кружок 🤳\n{challenge_text}',
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )

        # del CAPTCHA_SOLUTIONS[user_id]
        return CHALLENGE

    await update.message.reply_text('📛 Неверный ввод, отмена!')
    return ConversationHandler.END


async def verify_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = session.query(User).filter_by(telegram_id=user_id).first()
    
    current_date = get_current_time()
    current_lecture = get_lecture_number(current_date)
    
    video_path = Path.cwd() / 'data' / 'proofs' / \
        f'{user_id}_{current_date.strftime("%d%m%Y_%H%M%S")}.mp4'

    video_note = update.message.video_note
    video = await context.bot.get_file(video_note.file_id)
    await video.download_to_drive(video_path)

    attendance = Attendance(
        timestamp=current_date,
        lecture_number=current_lecture,
        user_id=user.id,
        challenge=CHALLENGE_SOLUTIONS[user_id],
        video_path=video_path.name
    )
    session.add(attendance)
    session.commit()

    await update.message.reply_text(
        f'👌 Отметка поставлена!\n'
        f'✍ {user.last_name} {user.first_name} {user.middle_name}\n'
        f'🔔 {current_date.strftime("%d.%m.%Y %H:%M:%S")} - {current_lecture} пара\n\n'
        f'👁‍🗨 Задание `{video_path.name}`:\n{CHALLENGE_SOLUTIONS[user_id]}\n',
        parse_mode='Markdown'
    )
    
    await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=CHALLENGE_MESSAGES[user_id].message_id
        )
    
    # del CHALLENGE_SOLUTIONS[user_id]
    # del CHALLENGE_MESSAGES[user_id]
    return ConversationHandler.END


async def no_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    await update.message.reply_text('📛 Неверный ввод, отмена!')
    await update.message.delete()
    
    await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=CHALLENGE_MESSAGES[user_id].message_id
        )
    
    # del CHALLENGE_MESSAGES[user_id]
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer('Отменено!')
    
    await query.delete_message()
    return ConversationHandler.END


def handlers() -> list[ConversationHandler]:
    attendance_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^✍️ Отметиться$"), attendance)
        ],
        states={
            CAPTCHA: [
                MessageHandler(filters.TEXT, verify_captcha)
            ],
            CHALLENGE: [
                MessageHandler(filters.VIDEO_NOTE, verify_challenge),
                MessageHandler(filters.TEXT, no_video)
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel$'),]
    )
    return [attendance_handler]
