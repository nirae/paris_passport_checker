#! /usr/bin/env python3

"""Slot checker for 42 projects"""

import re
import os
import sys
import time
import threading
import logging as log
import argparse as arg
from datetime import date, datetime, timedelta

import yaml
import httpx

# https://python-telegram-bot.readthedocs.io/en/stable/
import telegram

# https://www.crummy.com/software/BeautifulSoup/bs4/doc/
from bs4 import BeautifulSoup

# https://marshmallow.readthedocs.io/en/stable/
from marshmallow import Schema, fields, validate, validates, post_load, ValidationError

from exceptions import passport_checker_exception, PassportCheckerException
from env import PATH_CONFIG, PARIS_TELESERVICE_URL

log.basicConfig(
    format="%(asctime)s %(levelname)7s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    level=log.INFO,
)


class Site:
    """Handle request to the website"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Set up an httpx client to connect to the Site

        Initializes the client only if none is active.
        """
        if self._client is None:
            self._client = httpx.Client()
        return self._client

    def get_appointments(self, from_date: str, from_time: str, to_date: str, to_time: str, person_number: int, days: list, retries=0):
        """Query a project page for available evaluation slots

        Return status code 404 (unknown project) and 403 (unavailable corrections),
        trigger a warning log.

        Raises an error in case of any httpx related network error.

        Args:
            - start: start of the disponibility period
            - end: end of the disponibility period
            - retries: number of retries in case of network error
        """

        max_retries = 10
        try:
            data = {
                'page': 'appointmentsearch',
                'role': 'none',
                'from_date': from_date,
                'from_time': from_time,
                'to_date': to_date,
                'to_time': to_time,
                'from_day_minute': 360,
                'to_day_minute': 1260,
                'nb_consecutive_slots': person_number,
                'days_of_week': days,
                'action_search': 'Rechercher'
            }
            resp = self.client.post(PARIS_TELESERVICE_URL, data=data, timeout=10, follow_redirects=True)

            if resp.status_code == 404:
                log.warning("Get 404")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            places = soup.select(".nextAvailableAppointments > div")
            result = []
            for place in places:
                location = place.select_one("h4").text.strip()
                address = place.select_one(":nth-child(2) > div > p").text.strip()
                slots = place.select("ul > li > a")
                for slot in slots:
                    date_str = slot.text.strip()
                    date = datetime.strptime(date_str, "%d %B %Y %H:%M")
                    result.append({
                        'location': location,
                        'address': address,
                        'date': date
                    })
            return result
        except (httpx.RequestError, httpx.ReadTimeout, httpx.ConnectError) as err:
            if retries < max_retries:
                log.debug(
                    f"Failed attempt #{retries} to get appointments (max {max_retries})"
                )
                time.sleep(2)
                return self.get_appointments(
                    from_date=from_date,
                    from_time=from_time,
                    to_date=to_date,
                    to_time=to_time,
                    person_number=person_number,
                    days=days,
                    retries=retries + 1
                )
            passport_checker_exception(err, "Unable to get appointments")


class Config:
    """Load and check configuration"""

    # pylint: disable=too-many-instance-attributes
    # Nine is reasonable in this case.

    class Schema(Schema):
        """Template to check that configuration is valid"""

        senders = ["telegram"]
        telegram_options = ["chat_id", "token"]

        to_date = fields.Str(required=True)
        from_date = fields.Str(required=False, default="")
        from_time = fields.Str(required=False, default="06:00")
        to_time = fields.Str(required=False, default="21:00")
        person_number = fields.Int(required=False, default=1)
        days = fields.List(fields.Int(required=True), required=False, default=[1, 2, 3, 4, 5, 6, 7])
        send = fields.Dict(
            keys=fields.Str(required=True, validate=validate.OneOf(senders)),
            values=fields.Dict(
                keys=fields.Str(
                    required=True, validate=validate.OneOf(telegram_options)
                ),
                values=fields.Str(required=True),
                required=True,
            ),
            required=False,
        )
        refresh = fields.Int(required=False, default=30)

        @post_load
        def create_processing(self, data, **_):
            """Hand over validated configuration"""
            # pylint: disable=no-self-use
            # self is required for the Marshmallow decorator

            return Config(**data)

    def __init__(
        self,
        to_date,
        from_date="",
        from_time="06:00",
        to_time="21:00",
        person_number=1,
        days=[1, 2, 3, 4, 5, 6, 7],
        send=None,
        refresh=30
    ):
        """Store configuration"""

        self.from_date = from_date
        self.from_time = from_time
        self.to_date = to_date
        self.to_time = to_time
        self.person_number = person_number
        self.days = days
        self.refresh = refresh
        self.sender = send
        self.mtime = time.time()

    @property
    def updated(self):
        """Check if config was updated since last loaded"""

        if self.mtime < os.path.getmtime(PATH_CONFIG):
            log.info("Config file has changed since starting the Slot Checkout")
            return True
        return False

    @staticmethod
    def load():
        """Load configuration from file

        Returns a Config object
        """
        log.info("Loading configuration from file %s", PATH_CONFIG)
        try:
            log.info("Start load config")
            with open(PATH_CONFIG) as config:
                data = yaml.load(config, Loader=yaml.FullLoader)
            schema = Config.Schema()
            return schema.load(data)
        except (FileNotFoundError, ValidationError, yaml.parser.ParserError) as err:
            passport_checker_exception(
                err, "There seems to be a problem with your configuration file"
            )


class Sender:
    """Handle interaction with a message channels"""

    def __init__(self, sender):
        """Get ready to send messages"""

        self.sender = sender
        for key, value in self.sender.items():
            self.send_option = key
            self.sender_config = value
        self.bot = telegram.Bot(token=self.sender_config["token"])

    def send_telegram(self, message):
        """Send a message to a telegram bot"""

        self.bot.send_message(
            text=message, parse_mode="HTML", chat_id=self.sender_config["chat_id"]
        )

    def send(self, message):
        """Send message to the chosen channels"""

        if self.send_option == "telegram":
            self.send_telegram(message)


class Checker:
    """Check the user's project pages for available slots"""

    def __init__(self, config: Config):
        """Get ready to check for slots"""

        log.debug("Initializing the checker")
        self.config = config
        self._site = None
        self._sender = None
        self.health_delay = 60
        self.health = threading.Thread(target=self.health_loop)
        # Needed so that calls to sys.exit() don't hang with never-ending thread
        # https://stackoverflow.com/questions/38804988/what-does-sys-exit-really-do-with-multiple-threads
        self.health.daemon = True
        self.health.start()

    @property
    def sender(self):
        """Set up a Sender object if none is active"""

        if self.config.sender and self._sender is None:
            self._sender = Sender(self.config.sender)
        return self._sender

    @property
    def site(self):
        """Valid connection the site

        If there is no active connection or credentials have changed since logging in,
        a new connection is open. Otherwise, the connection remains unchanged.
        """

        if (
            self._site is None
        ):
            self._site = Site()
        return self._site

    def health_loop(self):
        """Log regularly that the checker is alive"""

        while True:
            log.info("[Health check] slot checker still alive")
            time.sleep(self.health_delay)

    def run(self):
        """Run the slot checker

        For all configured projects, continuously get available slots within disponibility timeframe
        Send positive results to desired message channels at least once (if no-spam is True)
        """

        log.info("Check for available slots")
        with self.site.client:
            while True:
                if self.config.updated:
                    self.config = Config.load()
                    return self.run()

                slots = self.site.get_appointments(
                    from_date=self.config.from_date,
                    from_time=self.config.from_time,
                    to_date=self.config.to_date,
                    to_time=self.config.to_time,
                    person_number=self.config.person_number,
                    days=self.config.days
                )

                for slot in slots:
                    date = slot['date'].strftime("%d %B %Y %H:%M")
                    log.info(f"Found slot : {slot['location']}, {slot['address']} -> {date}")
                    log.info("send to %s", self.sender.send_option)
                    message = f"""Rendez-vous ! <b>{date}</b>
                    <b>{slot['location']}</b>
                    {slot['address']}
                    https://teleservices.paris.fr/rdvtitres/jsp/site/Portal.jsp?page=appointmentsearch&view=search&category=titres"""
                    self.sender.send(message)
                time.sleep(self.config.refresh)


if __name__ == "__main__":

    parser = arg.ArgumentParser(description="Passport appointments checker for Paris")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="include debugging logs"
    )
    args = parser.parse_args()

    if os.environ.get("SLOT_CHECKER_DEBUG") or args.verbose:
        log.getLogger().setLevel(log.DEBUG)
    try:
        checker = Checker(Config.load())
        checker.run()
    except PassportCheckerException as err:
        log.error("Aborting following an error while running the Slot Checker")
        sys.exit(err.error_code)
