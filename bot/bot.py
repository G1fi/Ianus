from telegram.ext import ApplicationBuilder, AIORateLimiter

from .admin import handlers as admin_handlers
from .default import handlers as default_handlers
from .attendance import handlers as attendance_handlers
from config import BOT_TOKEN


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()
    
    for handler in admin_handlers():
        application.add_handler(handler)

    for handler in attendance_handlers():
        application.add_handler(handler)
    
    for handler in default_handlers():
        application.add_handler(handler)
    
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
