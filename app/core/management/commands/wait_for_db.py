"""
Django command to wait for the database to be availabe

"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """ Django command to wait for databas."""
    
    def handle(self, *args, **options):
        pass
