from os import path
from time import sleep

from IPython import embed
from .waveshare_epd import epd2in13_V2
from PIL import Image, ImageDraw, ImageFont

from .utils import start_epd, stop_epd, create_image, draw_time, flush_screen, FONT_PATH

def main():
    print("""
    start_epd(full_update=True) -> EPD
    stop_epd(epd) -> None
    create_image(epd) -> Image
    draw_time(epd, seconds=60) -> None
    flush_screen(epd, count=5) -> None

    epd.init(PART_UPDATE)
    epd.init(FULL_UPDATE)
    epd.Clear(0x00)
    epd.Clear(0xFF)

    FONT_PATH = "/usr/share/fonts/truetype/msttcorefonts/"

    epd = start_epd()
    font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 20)
    image = create_image(epd)
    draw = ImageDraw.Draw(image)

    draw.text((0, 0), "Hello, World!", font=font, fill=0)
    epd.display(epd.getbuffer(image))
    sleep(5)
    draw.rectangle((0, 0, epd.height, epd.width), fill=0xFF)
    draw.text((0, 0), "Hello, again!", font=font, fill=0)
    epd.display(epd.getbuffer(image))
    sleep(5)
    stop_epd(epd)

    """)
    epd = start_epd()
    font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 20)
    image = create_image(epd)
    draw = ImageDraw.Draw(image)

    embed()


if __name__ == "__main__":
    main()
