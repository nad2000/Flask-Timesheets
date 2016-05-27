from datetime import datetime
from peewee import Model, CharField, DateTimeField, ForeignKeyField, TextField, IntegerField
from flask_timesheets import db, FlaskDB
from hashlib import md5
from flask.ext.security import Security, PeeweeUserDatastore, UserMixin, RoleMixin, login_required
from playhouse.fields import ManyToManyField
from peewee import drop_model_tables

class Company(db.Model):
    name = CharField()
    code = CharField()
    
class Role(db.Model, RoleMixin):
    name = CharField(unique=True)
    description = TextField(null=True)
    
class User(db.Model, UserMixin):
    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    first_name = CharField()
    last_name = CharField()
    workplace = ForeignKeyField(Company, related_name='works_for')
    roles = ManyToManyField(Role, related_name='users')
    approves_for = ManyToManyField(Company, related_name='verified_by')
    
    class Meta:
        order_by = ('username',)

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

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


def create_tables():
    """
    Create all DB tables
    """
    if isinstance(db, FlaskDB):
        _db = db.database
    else:
        _db = db
    _db.connect()
    _db.create_tables((
        Company,
        Role,
        User,
        BreakType,
        User.roles.get_through_model(),
        User.approves_for.get_through_model()))
        
def drop_talbes():
    """
    Drop all model tables
    """
    models =  [User.roles.get_through_model(), User.approves_for.get_through_model()]
    models.extend(m for m in globals().values() if isinstance(m, type)  and issubclass(m, db.Model))
    drop_model_tables(models, fail_silently=True)
