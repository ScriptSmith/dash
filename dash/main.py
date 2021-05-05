#!/usr/bin/env python

from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO
from itertools import cycle
from os import path, environ
from random import choice
import socket
from time import sleep

from .waveshare_epd import epd2in13_V2
from .utils import start_epd, stop_epd, create_image, draw_time, get_text_dimensions, FONT_PATH

from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests


class Screen(ABC):
    MENU_OFFSET = 22
    CANVAS_OFFSET = 110

    def __init__(self, epd, full_update=True):
        self.epd = epd
        self.full_update = full_update

        self.image = create_image(epd)
        self.draw = ImageDraw.Draw(self.image)
        self.menu_font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 20)
        self.canvas_font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 14)

        self.logo = self.get_logo()

    def loop(self):

        self.clear_image()
        self.stats = self.get_stats()

        menu_rect = self.draw_menu()
        self.draw_logo()
        self.draw_canvas()

        self.epd.init(self.epd.FULL_UPDATE)

        if self.full_update:
            self.epd.display(self.epd.getbuffer(self.image))
            sleep(60 - datetime.now().second)

        else:
            self.epd.displayPartBaseImage(self.epd.getbuffer(self.image))
            self.epd.init(self.epd.PART_UPDATE)

            for _ in range(60):
                start_time = datetime.now()

                self.draw.rectangle(menu_rect, fill=0xFF)
                menu_rect = self.draw_menu()
                self.epd.displayPartial(self.epd.getbuffer(self.image))

                sleep(1 - (datetime.now() - start_time).total_seconds())


    def clear_image(self):
        self.draw.rectangle((0, 0, self.epd.height, self.epd.width), fill=0xFF)

    def display_epd(self):
        image_buffer = self.epd.getbuffer(self.image)
        self.epd.display(image_buffer) if self.full_update else self.epd.displayPartial(image_buffer)

    def draw_components(self):

        self.draw_menu()
        self.display_epd()

    def draw_menu(self):
        clock = "%H:%M" if self.full_update else "%H:%M:%S"
        time_text = datetime.now().strftime(f"{clock} %a %d %b, %Y")
        self.draw.text((0, 0), time_text, font=self.menu_font, fill=0)
        return (0, 0) + get_text_dimensions(time_text, self.menu_font)

    @abstractmethod
    def get_logo(self) -> Image:
        pass

    @abstractmethod
    def draw_logo(self) -> Image:
        pass

    @abstractmethod
    def draw_canvas(self) -> Image:
        pass

    def get_stats(self):
        pass


class GithubScreen(Screen):
    LOGO_URL = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"

    def __init__(self, *args, **kwargs):
        self.github_user = environ.get("GITHUB_USER")

        super().__init__(*args, **kwargs)

    def get_logo(self):
        return Image.open(requests.get(self.LOGO_URL, stream=True).raw).resize((100, 100))

    def get_stats(self):
        return requests.get(f"https://api.github.com/users/{self.github_user}").json()

    def draw_logo(self):
        self.image.paste(self.logo, (0, self.MENU_OFFSET))

    def draw_canvas(self):
        lines = [
                "",
                self.github_user,
                f"Repos: {self.stats['public_repos']}",
                f"Followers: {self.stats['followers']}",
                f"Following: {self.stats['following']}",
        ]
        self.draw.multiline_text((self.CANVAS_OFFSET, self.MENU_OFFSET), "\n".join(lines), font=self.canvas_font, fill=0)

class JiraScreen(Screen):
    LOGO_URL = "https://test.atlassian.net/favicon.ico"

    def __init__(self, *args, **kwargs):
        self.jira_username = environ.get("JIRA_USERNAME")
        self.jira_password = environ.get("JIRA_PASSWORD")
        self.jira_group = environ.get("JIRA_GROUP")
        self.jira_query = environ.get("JIRA_QUERY")

        super().__init__(*args, **kwargs)

    def get_logo(self):
        return Image.open(BytesIO(requests.get(self.LOGO_URL).content)).convert("1", dither=0, colors=1).resize((80, 80))

    def get_stats(self):
        return requests.get(f"https://{self.jira_group}.atlassian.net/rest/api/2/search?jql={self.jira_query}", auth=(self.jira_username, self.jira_password)).json()

    def draw_logo(self):
        self.image.paste(self.logo, (0, self.MENU_OFFSET + 10))

    def draw_canvas(self):
        my_issues = []
        for issue in self.stats['issues']:
            if issue['fields'].get('assignee'):
                if issue['fields']['assignee']['emailAddress'] == self.jira_username:
                    my_issues.append(issue)
        in_progress = list(filter(lambda x: x['fields']['status']['name'] == "In Progress", my_issues))
        lines = [
            "",
            f"Issues: {len(my_issues)} / {self.stats['total']}",
            f"In progress: {len(in_progress)}",
        ]
        self.draw.multiline_text((self.CANVAS_OFFSET, self.MENU_OFFSET), "\n".join(lines), font=self.canvas_font, fill=0)

class FerryScreen(Screen):
    API_URL = "https://api.brisbane.qld.gov.au/external/smartrak/api/v1/stop-monitor"

    def __init__(self, *args, **kwargs):
        self.ferry_stop = environ.get("FERRY_STOP")

        super().__init__(*args, **kwargs)

    def get_logo(self):
        return Image.open('icons/ferry.png')

    def get_stats(self):
        return requests.get(self.API_URL, params={"monitoringRef": self.ferry_stop}).json()

    def draw_logo(self):
        self.image.paste(self.logo, (0, self.MENU_OFFSET))

    def draw_canvas(self):
        self.get_stats()
        timetable = [""]
        for ferry in self.stats['Siri']['ServiceDelivery']['StopMonitoringDelivery']['MonitoredStopVisit']:
            if not ferry['MonitoredVehicleJourney']['DirectionRef'] == "Upstream":
                continue

            aimed_departure = datetime.strptime(ferry['MonitoredVehicleJourney']['MonitoredCall']['AimedDepartureTime'], "%Y-%m-%dT%H:%M:%S")
            expected_departure = datetime.strptime(ferry['MonitoredVehicleJourney']['MonitoredCall']['ExpectedDepartureTime'], "%Y-%m-%dT%H:%M:%S")
            delta = (expected_departure - datetime.now()).total_seconds() // 60
            delay = (expected_departure - aimed_departure).total_seconds() // 60
            timetable.append(f"{expected_departure.strftime('%H:%M')} - {delta:.0f} min ({delay:+.0f})")


        self.draw.multiline_text((self.CANVAS_OFFSET, self.MENU_OFFSET), "\n".join(timetable[:5]), font=self.canvas_font, fill=0)

class IpScreen(Screen):
    def __init__(self, *args, **kwargs):
        self.font = ImageFont.truetype(path.join(FONT_PATH, "arial.ttf"), 30)

        super().__init__(*args, **kwargs)

    def get_logo(self):
        pass

    def draw_logo(self):
        pass

    def draw_canvas(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        local_ip_addr = s.getsockname()[0]
        self.draw.multiline_text((0, self.MENU_OFFSET), local_ip_addr, font=self.font, fill=0)

class CapScreen(Screen):
    LOGO_PATH = None
    MESSAGE = None

    def get_logo(self):
        return Image.open(self.LOGO_PATH).resize((80, 80))

    def draw_logo(self):
        self.image.paste(self.logo, (0, self.MENU_OFFSET + 10))

    def draw_canvas(self):
        self.draw.multiline_text((self.CANVAS_OFFSET, self.MENU_OFFSET + 30), choice(self.MESSAGES), font=self.menu_font, fill=0)

class GoodMorningScreen(CapScreen):
    LOGO_PATH = "icons/sun.png"
    MESSAGES = ["Good Morning!", "sup", "Hello", "G'day", "Well, well, well\nLook who it is...", "How'sit hangin?", "Ello, gov'na" "How farest \nthou?"]

class GoodNightScreen(CapScreen):
    LOGO_PATH = "icons/moon.png"
    MESSAGES = ["Good Night!", "cya", "Have a good one!", "l8r sk8r", "'Til we meet again", "Farewell", "À bientôt", "Keep the change\nYa filthy animal"]

def main():
    epd = start_epd()

    IpScreen(epd).loop()

    times = [
        (0, [GoodNightScreen]),
        (4, [GoodMorningScreen]),
        (9, [JiraScreen]),
        (10, [JiraScreen, GithubScreen]),
        (15, [FerryScreen]),
        (20, [GoodNightScreen]),
    ]

    try:
        while True:
            current_time = datetime.now()

            screens = None
            for t, t_screens in times:
                if current_time.hour < t:
                    break
                screens = t_screens

            screen = choice(screens)(epd)
            screen.loop()
    except KeyboardInterrupt:
        pass

    print()
    print("Done")
    stop_epd(epd)


if __name__ == "__main__":
    main()
