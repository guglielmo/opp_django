from opp.management.base import ImportCommand
from parser import readers, writers
__author__ = 'guglielmo'


class Command(ImportCommand):
    """
    Check votations at la Camera
    """
    help = "Check sedute at la Camera for the current and previous months"

    def handle(self, *labels, **options):
        super(Command, self).setup(*labels, **options)

        reader = readers.Camera17VotationsReader(self.logger)
        sittings = reader.read()

        writer = writers.JSONVotationsWriter(sittings, json_filename='test.json')
        writer.write()

        # writer = writers.OppDBVotationsWriter(self.logger)
        # writer.write_sittings(sittings, house='C')