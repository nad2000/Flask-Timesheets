from datetime import datetime
from peewee import Model, CharField, DateTimeField, ForeignKeyField, TextField, IntegerField
from flask_timesheets import db, FlaskDB
from hashlib import md5

class Company(db.Model):
    name = CharField()
    code = CharField()
    
# the user model specifies its fields (or columns) declaratively, like django
class User(db.Model):
    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    first_name = CharField()
    last_name = CharField()
    company_id = ForeignKeyField(Company, related_name='works_for')
    
    class Meta:
        order_by = ('username',)

    @property
    def full_name(self):
        return " ".join((self.first_name, self.last_name))

    def gravatar_url(self, size=80):
        return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % \
            (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

class BreakType(db.Model):
    code = CharField(unique=True)
    name = CharField()
    time_value = IntegerField()
    alternative_code = CharField(unique=True)

    class Meta:
        order_by = ('code',)
    
class UserCompany(db.Model):
    user_id = ForeignKeyField(User, related_name='verified_by')
    company_id = ForeignKeyField(Company, related_name='verifies_for')


def create_tables():
    if isinstance(db, FlaskDB):
        _db = db.database
    else:
        _db = db
    _db.connect()
    _db.create_tables([Company, User, BreakType, UserCompany])
