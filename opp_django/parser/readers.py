"""
Readers read data from the camera and senato websites (scraping).

They're completely agnostic with regards to the data already stored in databases
and just return the information contained in the site.

Operations are broken down into an atomic API, so that optimized reading
operations may be invoked at a higher level.
"""
from datetime import date, datetime, timedelta
import logging, logging.config
from bs4 import BeautifulSoup
from django.conf import settings
import re
import requests

__author__ = 'guglielmo'


class Camera17VotationsReader(object):
    """
    Class that reads votations information from http://www.camera.it
    and put it into a python data structure.

    a simple (cool) usage::

        from parser.readers import Camera17VotationsReader
        reader = Camera17VotationsReader()
        reader.get_votation_details('152_15')
    """

    LEGISLATURE = 17
    DOCUMENTS_CAMERA_BASE_URL = "http://documenti.camera.it/votazioni/votazionitutte"
    DOCUMENTS_CAMERA_LIST_URL = "{}/risultatidb.asp".format(DOCUMENTS_CAMERA_BASE_URL)
    DOCUMENTS_CAMERA_DETAIL_URL = "{}/schedaVotazione.asp".format(DOCUMENTS_CAMERA_BASE_URL)
    RESOCONTI_ASSEMBLEA_URL = "http://www.camera.it/leg{}/207".format(LEGISLATURE)
    SEDUTA_REFERENCE_URL = "http://www.camera.it/Leg{}/410".format(LEGISLATURE)

    def __init__(self, logger=None):
        if logger is None:
            logging.config.dictConfig(settings.LOGGING)
            self.logger = logging.getLogger('console')
        else:
            self.logger = logger

    def get_sittings(self, year_month):
        """
        returns a list of sittings for the given year_month month

        :year_month: a string of the format "YYYY-MM"
        """
        year, month = year_month.split('-')

        # get resoconti assemblea page for this year and month
        ym_resoconti_uri = "{}?annomese={},{}".format(self.RESOCONTI_ASSEMBLEA_URL, year, month)
        r = requests.get(ym_resoconti_uri)
        self.logger.info("parsing: {}".format(ym_resoconti_uri))

        # get all links of class 'eleres_seduta'
        s = BeautifulSoup(r.content)
        a_sedute = s.find_all('a', class_='eleres_seduta')
        seduta_regexp = re.compile(r"(.+) n. (.+?) .+? (.+)")

        sittings = []
        for s in a_sedute:
            (domain, num, day) = seduta_regexp.match(s.text).groups()
            sittings.append({
                'num': num,
                'date': "{}-{}-{}".format(year, month, day),
                'reference_url': "{}?idSeduta={}".format(
                            self.SEDUTA_REFERENCE_URL, num
                )
            })

        self.logger.info("returning {} sittings".format(len(sittings)))
        return sittings

    def get_last_sittings(self, n_months_back=1):
        """
        Return the complete list of sittings for the current and last month
        """

        # compute current's and last's month and year, as YYYY-MM strings
        today = date.today()
        first = date(day=1, month=today.month, year=today.year)
        current_ym = datetime.strftime(today, '%Y-%m')

        last_month_last_day = first - timedelta(days=1)
        last_ym = datetime.strftime(last_month_last_day, '%Y-%m')


        # loop over last and current year-month
        sittings = []
        for ym in (current_ym, last_ym):
            sittings.extend(self.get_sittings(ym))

        return sittings

    def get_votations(self, sitting_date):
        """
        get the list of all votations for a sitting in a given date
        the date is a python date object, or a 'YYYY-MM-DD' string

        for each votations, the following data are returned:

          - ref_numbers - sitting and votation numbers,
                          separated by an underscore character (181_1)
          - uri         - the uri of the votation details page
        """
        uri_template = self.DOCUMENTS_CAMERA_LIST_URL + "?" + \
            "action=Votazioni&PagCorr={}&Legislatura={}&" \
            "CDDGIORNO={}&CDDMESE={}&CDDANNO={}"

        if isinstance(sitting_date, str):
            sitting_date = datetime.strptime(sitting_date, '%Y-%m-%d')

        # fetch first page
        pagina = 1
        s_uri = uri_template.format(pagina, self.LEGISLATURE, sitting_date.day, sitting_date.month, sitting_date.year)
        r = requests.get(s_uri)
        c = BeautifulSoup(r.content)
        self.logger.debug("fetching from url: {}".format(s_uri))


        # when there are no votes, return an empty list
        p_campo = c.find_all('p', 'campo')
        if p_campo and 'attenzione' in p_campo[0].string.lower():
            self.logger.info("  Non ci sono votazioni nella seduta.")
            return []
        else:
            # initializa return list
            ret_votations = []

            # infinite loop to browse different pages
            while (True):
                # append votations in the page to return list
                for a_voto in c.select('div.itemV a'):
                    votation_uri = self.DOCUMENTS_CAMERA_BASE_URL + a_voto['href']
                    votation_ref_numbers = re.match(r'.*RifVotazione=(.*)&tipo.*', votation_uri).group(1)
                    _, num_votazione = votation_ref_numbers.split("_")

                    ret_votations.append({ 'ref_numbers': votation_ref_numbers, 'uri': votation_uri })

                if c.select('a#Prossima'):
                    # fetch next page
                    pagina += 1
                    s_uri = uri_template.format(pagina, self.LEGISLATURE, sitting_date.day, sitting_date.month, sitting_date.year)
                    r = requests.get(s_uri)
                    c = BeautifulSoup(r.content)
                    self.logger.debug("fetching from url: {}".format(s_uri))
                else:
                    # this was the last page; break the infinite while loop
                    break

            return ret_votations


    def get_votation_details(self, votation_ref):
        # prepare uri and fetch content
        uri_template = self.DOCUMENTS_CAMERA_DETAIL_URL + "?" + \
            "Legislatura={}&RifVotazione={}"
        v_uri = uri_template.format(self.LEGISLATURE, votation_ref)
        r = requests.get(v_uri)
        c = BeautifulSoup(r.content)
        self.logger.debug("fetching from url: {}".format(v_uri))

        # scrape title
        votation_title = c.find_all('div', id='titolo')[0].string.strip()

        # scrape type
        votation_type = re.match(
            r"Votazione (.*) n\..*",
            c.find_all('div', class_='verde12')[0].contents[0].string.strip()
        ).group(1)

        # get the votation number, from the passed votation_ref argument
        _, votation_number = votation_ref.split("_")

        # scrape votation summarized numbers and the final result (approval or reject)
        trs = c.select('table.esito tr')[1:-1]
        votation_summary = {}
        for tr in trs:
            k, v = [td.string.strip() for td in tr.find_all('td')]
            votation_summary[k] = v

        votation_result = c.select('table.esito tr')[-1].find_all('td')[0].contents[0]


        # get all the single votes
        votation_detail = {}
        trs = c.select('table.deputati tr')[1:]
        for tr in trs:
            k1, v1, _, k2, v2 = [td.string for td in tr.find_all('td')]
            votation_detail.update({
                k1: v1,
                k2: v2,
            })


        # prepare return structure
        ret_votation = {
            'title': votation_title,
            'number': votation_number,
            'type': votation_type,
            'summary': votation_summary,
            'result': votation_result,
            'detail': votation_detail,
        }

        return ret_votation


    def read(self):
        """
        full read operation

        reads through recursively: sittings, votations, votation details

        for the current and previous month

        watch out, may take long time and lots of requests!!!
        """
        sittings = self.get_last_sittings()
        for sitting in sittings:
            votations = self.get_votations(sitting['date'])

            for votation in votations:
                votation.update({
                    'votation_details': self.get_votation_details(votation['ref_numbers'])
                })

            sitting.update({
                'votations': votations
            })

        return sittings