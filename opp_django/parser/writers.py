import json
import logging, logging.config
from django.conf import settings
from opp.models import Seduta

__author__ = 'guglielmo'

class JSONVotationsWriter(object):
    """
    Write sittings to a JSON stream (may be a file)
    """

    def __init__(self, data, json_filename=None):
        self.data = data
        self.json_filename = json_filename

    def write(self):
        if self.json_filename:
            f = open(self.json_filename, 'w')
            f.write(json.dumps(self.data, indent=4))
        else:
            print(json.dumps(self.data, indent=4))


class OppDBVotationsWriter(object):
    """

    """

    def __init__(self, logger=None):
        if logger is None:
            logging.config.dictConfig(settings.LOGGING)
            self.logger = logging.getLogger('console')
        else:
            self.logger = logger


    def write_sittings(self, sittings, house='C', legislature=17):
        """
        Create sittings if non-existing.
        Log creation or detection of the sitting.
        """
        for sitting in sittings:
            # get_or_create the seduta in the DB
            s, created = Seduta.objects.get_or_create(
                house=house,
                legislatura=legislature,
                number=sitting['num'],
                defaults={
                    'is_imported': 0,
                    'date':sitting['date'],
                    'reference_url': sitting['reference_url']
                }
            )
            if created:
                self.logger.info("seduta created. num: {0}, day: {1}, id: {2}".format(sitting['num'], sitting['date'], s.id))
            else:
                self.logger.info("seduta found. num: {0}, day: {1}, id: {2}".format(sitting['num'], sitting['date'], s.id))

