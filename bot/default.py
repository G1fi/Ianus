from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

from database.db_setup import session
from database.models import User


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [['✍️ Отметиться'], ['💆‍♂️ Профиль']],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_first_name = update.message.from_user.first_name
    await update.message.delete()

    await update.message.reply_text(
        f'*👋 Привет, {user_first_name}!\n'
        '🫶 Добро пожаловать в бота учёта посещаемости.\n\n'
        '/reg - зарегистрироваться\n'
        '/group - выбрать группу\n'
        '/start - обновить бота*\n\n'
        'Продолжая использовать данного бота, '
        'вы добровольно соглашаетесь на обработку '
        'и хранение ваших персональных данных, '
        'включая возможные видеозаписи с вашим участием, '
        'в соответствии с законодательством Российской Федерации.',
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )


async def reg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    args = context.args
    
    await update.message.delete()
    
    if len(args) != 3:
        await update.message.reply_text(
            '❌ Некорректный ввод, используй так:\n'
            '`/reg Иванов Иван Иванович`',
            parse_mode='Markdown'
        )
        return
    
    last_name, first_name, middle_name = args
    existing_user = session.query(User).filter_by(telegram_id=user.id).first()

    new_name = f'{last_name} {first_name} {middle_name}'
    
    if existing_user:
        old_name = f'{existing_user.last_name} {existing_user.first_name} {existing_user.middle_name}'
        
        existing_user.first_name = first_name
        existing_user.middle_name = middle_name
        existing_user.last_name = last_name
        session.commit()

        await update.message.reply_text(
            f'🎓 Данные обновлены!\n'
            f'{old_name} > {new_name}'
        )
    else:
        new_user = User(
            telegram_id=user.id,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name
        )
        session.add(new_user)
        session.commit()

        await update.message.reply_text(
            f'🎓 Регистрация успешна, {new_name}!'
        )


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    args = context.args
    
    await update.message.delete()
    
    if len(args) != 1 or not args[0].isdigit() or args[0] not in ('1', '2'):
        await update.message.reply_text(
            '❌ Некорректный ввод, используй так:\n'
            '`/group 1`\n'
            '`/group 2`\n',
            parse_mode='Markdown'
        )
        return

    group_number = int(args[0])
    existing_user = session.query(User).filter_by(telegram_id=user.id).first()

    if existing_user:
        existing_user.subgroup = group_number
        session.commit()
        
        await update.message.reply_text(
            f'💼 Подгруппа изменена на {group_number}!'
        )
    else:
        await update.message.reply_text(
            '❌ Сначала зарегистрируйся - /reg'
        )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()

    await update.message.delete()

    if existing_user:
        await update.message.reply_text(
            f'💆‍♂️ Профиль №{existing_user.id}\n\n'
            f'🗃️ Telegram ID: `{existing_user.telegram_id}`\n'
            f'🎓 ФИО: `{existing_user.last_name} {existing_user.first_name} {existing_user.middle_name}`\n'
            f'💼 Подгруппа: `{existing_user.subgroup}`',
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            '❌ Сначала зарегистрируйся - /reg'
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer('Отменено!')
    
    await query.delete_message()
    return ConversationHandler.END


def handlers():
    return [
        MessageHandler(filters.TEXT & filters.Regex('^💆‍♂️ Профиль$'), profile),
        CommandHandler('start', start),
        CommandHandler('reg', reg),
        CommandHandler('group', group),
        CommandHandler('help', start),
        CallbackQueryHandler(cancel, pattern='^cancel$')
    ]
