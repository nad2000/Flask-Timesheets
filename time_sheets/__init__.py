from flask import Flask, redirect, url_for, request, session, abort
from flask_security import current_user
from functools import wraps
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from playhouse.flask_utils import FlaskDB  ### useless
from peewee import SqliteDatabase
from werkzeug.routing import BaseConverter
from flask_bcrypt import Bcrypt
from flask_security.utils import encrypt_password
from datetime import date, timedelta as _timedelta, datetime
import logging
import click
from faker import Faker
import os, sys
from itertools import product
from datetime import time
from . import settings

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
app.config.from_object(settings)
# db = FlaskDB(app)
db = SqliteDatabase('app.db')
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

from . import views
from . import models
from .models import *


@app.cli.command()
@click.option("-d", "--drop", is_flag=True, help="Drop tables before creating...")
@click.option("-f", "--force", is_flag=True, help="Enforce table creation.")
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    help="Shows SQL statements that get sent to the server or DB.")
def initdb(create=False, drop=False, force=False, verbose=False):
    """Initialize the database."""
    if verbose:
        logger = logging.getLogger("peewee")
        if logger:
            logger.setLevel(logging.DEBUG)
            logger.addHandler(logging.StreamHandler())

    if drop and force:
        models.drop_tables()

    try:
        models.create_tables()
    except Exception:
        app.logger.exception("Failed to create tables...")

    for c, n, l in [
        ("5H", "5 hrs", 300),
        ("HH", "1/2 hr", 30),
        ("1H", "1 hr", 60),
        ("1.5H", "1 1/2 hr", 90),
        ("2H", "2 hrs", 120),
        ("15M", "15 min", 15),
        ("45M", "45 min", 45),
        ("1H15M", "1 hr 15 min", 75),
        ("1H45M", "1 hr 45 min", 105),
        ("2H15M", "2 hrs 15 min", 135),
        ("2H30M", "2 hrs 30 min", 150),
        ("2H45M", "2 hrs 45 min", 165),
        ("3H0M", "3 hrs ", 180),
        ("3H15M", "3 hrs 15 min", 195),
        ("3H30M", "3 hrs 30 min", 210),
        ("3H45M", "3 hrs 45 min", 225),
        ("4H0M", "4 hrs ", 240),
        ("4H15M", "4 hrs 15 min", 255),
        ("4H30M", "4 hrs 30 min", 270),
        ("4H45M", "4 hrs 45 min", 285),
    ]:
        Break.get_or_create(code=c, name=n, minutes=l)

    # Create all roles:
    user_datastore.create_role(name="emp")
    user_datastore.create_role(name="approver")
    user_datastore.create_role(name="admin")


@app.cli.command("crtestdata")
@click.option(
    "-V",
    "--verbose",
    is_flag=True,
    help="Shows SQL statements that get sent to the server or DB.")
def add_test_data(verbose=False):
    """Add some test data."""
    if verbose:
        logger = logging.getLogger("peewee")
        if logger:
            logger.setLevel(logging.DEBUG)
            logger.addHandler(logging.StreamHandler())

    fake = Faker()
    fake.seed(42)


    for (c,
         n) in [('Z4M4Q0', fake.company()), ('B4J4L6', fake.company()), ('Y9P9S3', fake.company()),
                ('V9A5K4', fake.company()), ('Y0U5B3', fake.company()), ('T3N2Y6', fake.company()),
                ('Q6U3Y9', fake.company()), ('W9J2M9', fake.company()), ('Y3Z9T9', fake.company()),
                ('R2H4P5', fake.company())]:
        Company.get_or_create(code=c, name=n)

    # Create all roles:
    emp = user_datastore.find_role("emp")
    approver = user_datastore.find_role("approver")
    admin = user_datastore.find_role("admin")

    # Test Users
    with app.app_context():
        test_password = encrypt_password('12345')
    for id, (username, email, first_name, last_name) in enumerate(
        (('user0', fake.email(), fake.first_name(), fake.last_name()),
         ('user1', fake.email(), fake.first_name(), fake.last_name()),
         ('user2', fake.email(), fake.first_name(), fake.last_name()),
         ('approver0', fake.email(), fake.first_name(), fake.last_name()),
         ('approver1', fake.email(), fake.first_name(), fake.last_name()),
         ('approver2', fake.email(), fake.first_name(), fake.last_name()),
         ('admin0', fake.email(), fake.first_name(), fake.last_name()),
         ('admin1', fake.email(), fake.first_name(), fake.last_name()),
         ('admin2', fake.email(), fake.first_name(), fake.last_name())), 1):
        user = user_datastore.create_user(
            username=username,
            #code=username.upper(),
            email=email,
            password=test_password,
            first_name=first_name,
            last_name=last_name,
            workplace=Company.get(id=id))
        user.save()
        if "user" in username:
            user.roles = [emp]
        else:
            user.approves_for = [Company.get(id=company_id) for company_id in range(id, id + 2)]
            user.roles.add(approver)
            if "admin" in username:
                user.roles.add(admin)
        user.save()

    # Timesheet entires
    week_dates = list(week_day_dates())
    for no, (user, day) in enumerate(product(User.select(), week_dates)):
        entry = Entry(
            date=day,
            user=user,
            started_at=time(7, no * 10 % 60, 0),
            finished_at=time(16, no * 7 % 60, 0),
            break_for=Break.get(id=no % 20 + 1))
        entry.save()


@app.cli.command("cradmin")
@click.option("-f", "--force", is_flag=True, help="Enforce creation of the super-user.")
@click.option("-V", "--verbose", is_flag=True, help="Shows SQL statements.")
@click.option("-F", "--first-name", help="User first name.")
@click.option("-L", "--last-name", help="User last name.")
@click.option("-O", "--org-name", help="Organisation name.")
@click.option("-E", "--email", help="User email.")
@click.option("-P", "--password", help="User password.")
@click.argument("username", nargs=1)
def create_administrator(username,
                         email=None,
                         first_name=None,
                         last_name=None,
                         force=False,
                         verbose=False,
                         password="p455w0rd",
                         org_name=None):
    """Create a hub administrator, an organisation and link the user to the Organisation."""
    if verbose:
        logger = logging.getLogger("peewee")
        if logger:
            logger.setLevel(logging.DEBUG)
            logger.addHandler(logging.StreamHandler())
    if not models.User.table_exists() or not models.Organisation.table_exists():
        app.logger.error(
            "Database tables doensn't exist. Please, firts initialize the datatabase.")
        sys.exit(1)

    with app.app_context():
        password = encrypt_password(password)

    org = Company.select().where(Company.name == org_name).first()

    user, created = user_datastore.user_model.get_or_create(
        username=username,
        #code=username.upper(),
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        workplace=org)
    if created:
        admin_role, _ = user_datastore.role_model.get_or_create("admin")
        user.roles.add(admin_role)
        user.save()
        if org:
            user.approves_for = [org]
            approver_role, _ = user_datastore.role_model.get_or_create("approver")
            user.roles.add(approver_role)
            user.save()
    else:
        app.logger.warnig("User '%s' already exists." % username)
