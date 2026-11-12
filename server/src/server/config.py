import os

basedir = os.path.abspath(os.path.dirname(__file__))


# XXX: Need separate config for testing, development, and production
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL'
    ) or 'sqlite:///' + os.path.join(basedir, 'app.db')


def setup_logger():
    import logging

    class IgnorePendingRequests(logging.Filter):
        def filter(self, record):
            return '/api/students/pending' not in record.getMessage()

    logging.getLogger('werkzeug').addFilter(IgnorePendingRequests())
