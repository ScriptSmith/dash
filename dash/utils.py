from datetime import datetime
from os import path
from time import sleep

from .waveshare_epd import epd2in13_V2
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/msttcorefonts/"

def start_epd(full_update=True):
    epd = epd2in13_V2.EPD()
    epd.init(epd.FULL_UPDATE if full_update else epd.PART_UPDATE)
    epd.Clear(0xFF)
    return epd

def stop_epd(epd):
    flush_screen(epd, 5)

    epd.sleep()
    sleep(3)
    epd.Dev_exit()

def flush_screen(epd, count=5):
    epd.init(epd.FULL_UPDATE)

    flag = 0
    for _ in range(count):
        flag ^= 1
        epd.Clear(0xFF * flag)
        sleep(5)

    epd.Clear(0xFF)


def create_image(epd):
    return Image.new('1', (epd.height, epd.width), 0xFF)

def get_text_dimensions(text_string, font):
    # https://stackoverflow.com/a/46220683
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)

def draw_time(epd, seconds=60):
    font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 20)
    image = create_image(epd)
    draw = ImageDraw.Draw(image)

    epd.displayPartBaseImage(epd.getbuffer(image))

    epd.init(epd.PART_UPDATE)

    for _ in range(seconds):
        start_time = datetime.now()
        draw.rectangle((0, 0, epd.height, epd.width), fill=0xFF)

        time_text = datetime.now().strftime("%H:%M:%S %a %d %b, %Y")
        draw.text((0, 0), time_text, font=font, fill=0)

        epd.displayPartial(epd.getbuffer(image))
        sleep(1 - (datetime.now() - start_time).total_seconds())
