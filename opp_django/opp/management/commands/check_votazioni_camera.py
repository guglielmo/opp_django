# -*- coding: utf-8 -*-
from optparse import make_option
import logging
import re
from django.core import management
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, LabelCommand
import requests
from bs4 import BeautifulSoup
from opp.models import Seduta, Votazione


__author__ = 'guglielmo'
class Command(LabelCommand):
    """
    Check votations of a single seduta at la Camera
    """
    help = "Check votazioni at la Camera for a givev seduta (identified by internal ID)"

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    dest='dryrun',
                    action='store_true',
                    default=False,
                    help='Set the dry-run command mode: no record is written to the DB'),
        make_option('--legislature',
                    dest='legislature',
                    default='17',
                    help='The legislature. Defaults to 17.'),

    )

    logger = logging.getLogger('management')

    def handle_label(self, seduta_id, **options):

        dryrun = options['dryrun']
        legislature = options['legislature']

        s = Seduta.objects.get(pk=seduta_id)
        self.logger.info("Check votazioni for seduta {}. N. {}, date: {}".format(
            seduta_id, s.number, s.date
        ))


        uri_template = "http://documenti.camera.it/votazioni/votazionitutte/risultatidb.asp?" \
                "action=Votazioni&PagCorr={}&Legislatura={}&" \
                "CDDGIORNO={}&CDDMESE={}&CDDANNO={}"

        pagina = 1
        s_uri = uri_template.format(pagina, legislature, s.date.day, s.date.month, s.date.year)
        r = requests.get(s_uri)
        c = BeautifulSoup(r.content)
        self.logger.debug("url: {}".format(s_uri))

        p_campo = c.find_all('p', 'campo')
        if p_campo and 'attenzione' in p_campo[0].string.lower():
            # when no votes are there, set the is_imported flag to True, and just return
            self.logger.info("  Non ci sono votazioni nella seduta.")
            s.is_imported = 1
            s.save()
            return
        else:
            # parse all votations in a page, then simulate pressing the next page button, if found
            while (True):
                for a_voto in c.select('div.itemV a'):
                    voto_uri = "http://documenti.camera.it/votazioni/votazionitutte/" + a_voto['href']
                    rif_votazione = re.match(r'.*RifVotazione=(.*)&tipo.*', voto_uri).group(1)
                    _, num_votazione = rif_votazione.split("_")
                    try:
                        singolo_voto = Votazione.objects.get(sitting=s, numero_votazione=num_votazione)
                        if not singolo_voto.is_imported:
                            # import singola votazione, if votation was created,
                            # but import was not completed
                            management.call_command(
                                "check_singolo_voto_camera",s.id, singolo_voto.id, rif_votazione
                            )
                    except ObjectDoesNotExist:
                        # import singola votazione, if not existing in the DB
                        management.call_command(
                            "check_singolo_voto_camera", s.id, 0, rif_votazione
                        )
                        pass

                if c.select('a#Prossima'):
                    # fetch next page
                    pagina += 1
                    s_uri = uri_template.format(pagina, s.date.day, s.date.month, s.date.year)
                    r = requests.get(s_uri)
                    c = BeautifulSoup(r.content)
                    self.logger.debug("url: {}".format(s_uri))
                else:
                    # this was the last page; break the infinite while
                    break

        votazioni_seduta = Votazione.objects.filter(sitting=s).order_by('numero_votazione')
        # TODO: change title to sitting votations
        for v in votazioni_seduta:
            if 'ddl' in v.titolo.lower() and\
               ' - ' in v.titolo:
                numfase = re.match(r"", v.titolo).group(1)

        # check if all votations were correctly imported and
        # set is_imported to the seduta, too
        s_import_ok = True
        for v in votazioni_seduta:
            if not v.is_imported:
                s_import_ok = False
                break

        if s_import_ok:
            s.is_imported = 1
            s.save()
