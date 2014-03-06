# -*- coding: utf-8 -*-
from optparse import make_option
import logging
import re
from datetime import datetime, date, timedelta
from django.core import management
from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from opp.models import Seduta

__author__ = 'guglielmo'
class Command(BaseCommand):
    """
    Check votations at la Camera
    """
    help = "Check sedute at la Camera for the current and previous months"

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    dest='dryrun',
                    action='store_true',
                    default=False,
                    help='Set the dry-run command mode: no record is written to the DB'),
        make_option('--house',
                    dest='house',
                    default='C',
                    help='The house, may be (C)amera or (S)enato. Defaults to C.'),

    )

    logger = logging.getLogger('management')

    def handle(self, *args, **options):

        verbosity = options['verbosity']
        if verbosity == '0':
            self.logger.setLevel(logging.ERROR)
        elif verbosity == '1':
            self.logger.setLevel(logging.WARNING)
        elif verbosity == '2':
            self.logger.setLevel(logging.INFO)
        elif verbosity == '3':
            self.logger.setLevel(logging.DEBUG)


        self.dryrun = options['dryrun']
        house = options['house']

        # constants
        self.legislature = 17

        if house.lower() == 'c':
            self.handle_camera()
        elif house.lower() == 's':
            self.handle_senato()
        else:
            raise Exception("Wrong house parameter, use C or S.")


    def handle_camera(self, *args, **options):
        url_resoconti_assemblea = "http://www.camera.it/leg{}/207".format(self.legislature)
        url_seduta_reference = "http://www.camera.it/Leg{}/410".format(self.legislature)

        # compute current's and last's month and year, as YYYY-MM strings
        today = date.today()
        first = date(day=1, month=today.month, year=today.year)
        current_ym = datetime.strftime(today, '%Y-%m')

        last_month_last_day = first - timedelta(days=1)
        last_ym = datetime.strftime(last_month_last_day, '%Y-%m')


        # loop over last and current year-month
        for ym in (last_ym, current_ym):
            year, month = ym.split('-')

            # get resoconti assemblea page for this year and month
            ym_resoconti_uri = "{}?annomese={},{}".format(url_resoconti_assemblea, year, month)
            r = requests.get(ym_resoconti_uri)
            self.logger.info("parsing: {}".format(ym_resoconti_uri))
            s = BeautifulSoup(r.content)

            # get all links of class 'eleres_seduta'
            sedute = s.find_all('a', class_='eleres_seduta')

            seduta_regexp = re.compile(r"(.+) n. (.+?) .+? (.+)")
            for seduta in sedute:
                (domain, num, day) = seduta_regexp.match(seduta.text).groups()

                # get_or_create the seduta in the DB
                if not self.dryrun:
                    s, created = Seduta.objects.get_or_create(
                        house='C',
                        legislatura=self.legislature,
                        number=num,
                        defaults={
                            'is_imported': 0,
                            'date': "{}-{}-{}".format(year, month, day),
                            'reference_url': "{}?idSeduta={}".format(
                                url_seduta_reference, num
                            )
                        }
                    )
                    if created:
                        self.logger.info("seduta created. num: {}, day: {}, id: {}".format(num, day, s.id))
                    else:
                        self.logger.info("seduta found. num: {}, day: {}, id: {}".format(num, day, s.id))

                    if not s.is_imported:
                        management.call_command("check_votazioni_camera", s.id)

    def handle_senato(self, *args, **kwargs):
        raise Exception('Implement this!')
