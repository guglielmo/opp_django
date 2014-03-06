"""
Base classes for opp management commands.


"""
import logging
from optparse import make_option
from django.core.management.base import LabelCommand, BaseCommand

__author__ = 'guglielmo'

class ImportCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--house',
                    dest='house',
                    default='C',
                    help='The house, may be (C)amera or (S)enato. Defaults to C.'),
        make_option('--logger-alias',
                    dest='logger_alias',
                    default='management',
                    help='The logger alias to use, as defined in settings. Defaults to management.'),
        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    default=False,
                    help='Execute without actually writing into the DB'
        ),
    )

    help = "Base import class for the votations of Openparlamento"

    def setup(self, *labels, **options):
        self.logger = logging.getLogger(options['logger_alias'])
        self.dry_run = options['dry_run']
        self.house = options['house']

        # fix logger level according to verbosity
        verbosity = options['verbosity']
        if verbosity == '0':
            self.logger.setLevel(logging.ERROR)
        elif verbosity == '1':
            self.logger.setLevel(logging.WARNING)
        elif verbosity == '2':
            self.logger.setLevel(logging.INFO)
        elif verbosity == '3':
            self.logger.setLevel(logging.DEBUG)


    def handle(self, *labels, **options):
        """
        implement by first calling::

            super(Command, self).setup(*labels, **options)
        """
        raise Exception("Not implemented")


