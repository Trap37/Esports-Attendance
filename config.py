import logging
import os
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL'
    ) or 'sqlite:///' + os.path.join(basedir, 'app.db')


class IgnorePendingRequests(logging.Filter):
    def filter(self, record):
        return '/api/students/pending' not in record.getMessage()
