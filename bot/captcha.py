from datetime import datetime
from io import BytesIO
from random import choice, randint

from PIL import Image, ImageDraw, ImageFont
from pytz import timezone

from config import SHEDULE


def get_current_time() -> datetime:
    time_zone = timezone('Asia/Vladivostok')
    return datetime.now(time_zone)


def get_lecture_number(current_time: datetime) -> int | None:
    for index, (start, end) in enumerate(SHEDULE, start=1):
        if start <= current_time.time() < end:
            return index
        
    return None


def generate_captcha() -> tuple[BytesIO, str]:
    captcha_text = ''.join(choice('ERTYUPLKJHGFDSAZXCVBN23456789') for _ in range(5))
    
    image = Image.new('RGB', (150, 50), color=(255, 255, 255))
    font = ImageFont.load_default()
    draw = ImageDraw.Draw(image)
    
    for index, letter in enumerate(captcha_text):
        x = 15 + index * (150 / 5)
        y = randint(10, 30)
        draw.text(
            (x, y),
            letter,
            font=font,
            fill=(randint(0, 200), randint(0, 200), randint(0, 200), 128)
        )

    for _ in range(3):
        draw.line(
            [(randint(0, 150), randint(0, 50)), (randint(0, 150), randint(0, 50))],
            fill=(randint(0, 200), randint(0, 200), randint(0, 200)),
            width=1
        )
        
    for _ in range(120):
        draw.point(
            (randint(0, 150), randint(0, 50)),
            fill=(randint(0, 200), randint(0, 200), randint(0, 200), 128)
        )

    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)

    return output, captcha_text
