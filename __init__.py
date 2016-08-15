from flask import Flask, redirect, url_for, request, session, abort
from flask_security import current_user
from functools import wraps
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from playhouse.flask_utils import FlaskDB ### useless
from peewee import SqliteDatabase
from werkzeug.routing import BaseConverter
from flask_bcrypt import Bcrypt
from flask_security.utils import encrypt_password
from datetime import date, timedelta as _timedelta, datetime
import logging

class timedelta(_timedelta):
    
    def __str__(self):
        """
        String representation in form of "HH:MM"
        """
        hours = self.seconds // 3600
        minutes = (self.seconds % 3600) // 60
        return "%d:%02d" % (hours, minutes)
        


def str_to_date(str):
    return datetime.strptime(str, '%Y-%m-%d').date()


def str_to_time(str):
    return datetime.strptime(str, '%H:%M').time()
    
        
def current_week_ending_date():
    return date.today() + timedelta(days=(6 - date.today().weekday()))

    
def week_ending_dates(weeks=7):
   
    week_day_date = current_week_ending_date()
    for _ in range(7):
        yield week_day_date
        week_day_date -= timedelta(weeks=1)

    
def week_day_dates():
    """
    iterates though the current week day dates
    """
    week_day_date = date.today() - timedelta(days=date.today().weekday())
    for _ in range(7):
        yield week_day_date
        week_day_date += timedelta(days=1)

        
app = Flask(__name__)
app.config.from_object("settings")
db = FlaskDB(app)
bcrypt = Bcrypt(app)
admin = Admin(app, name='Time Sheets', template_mode='bootstrap3')


if app.debug:
    # Log all SQL queries:
    logger = logging.getLogger('peewee')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    from flask_debugtoolbar import DebugToolbarExtension
    toolbar = DebugToolbarExtension(app)
    
    
class DateConverter(BaseConverter):
    """
    Date value converter from a string formated as "YYYY-MM-DD"
    """
    def to_python(self, value):
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()

    def to_url(self, value):
        return value.isoformat()
app.url_map.converters['date'] = DateConverter

import views
