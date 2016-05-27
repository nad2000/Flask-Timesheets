from datetime import datetime
from peewee import Model, CharField, DateTimeField, ForeignKeyField, \
    TextField, IntegerField, DateField, TimeField, BooleanField
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

class Break(db.Model):
    code = CharField(unique=True)
    name = CharField()
    minutes = IntegerField()
    alternative_code = CharField(unique=True, null=True)

    class Meta:
        order_by = ('code',)
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return "Break(code=%r, name=%r, minutes=%r, alternative_code=%r)" \
            % (self.code, self.name, self.minutes, self.alternative_code)

class Entry(db.Model):
    date = DateField()
    user = ForeignKeyField(User, related_name='reported_by')
    approver = ForeignKeyField(User, related_name='approved_by', null=True)
    started_at = TimeField()
    finished_at = TimeField()
    modified_at = DateTimeField(default=datetime.now)
    comment = TextField(null=True)
    break_for = ForeignKeyField(Break, related_name='break_for', null=True)
    is_approved = BooleanField(default=False)
    
    @property
    def break_length(self):
        if self.break_for:
            return self.break_for.minutes
        else:
            return 0
    
    @property
    def total_min(self):
        total = (self.finished_at.hour - self.started_at.hour) * 60
        total += (self.finished_at.minute - self.started_at.minute)
        total -= self.break_length
        return total
                
    def __str__(self):
        output = "On %s from %s to %s" % (
            self.date.isoformat(), 
            self.started_at.strftime("%H:%M"),
            self.finished_at.strftime("%H:%M"))
        if self.break_for:
            output += " with beak for " +  self.break_for.name
        
        total_min = self.total_min
        output += ", total: %d:%02d" % (total_min//60, total_min%60) 
            
        return output

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
        Break,
        Entry,
        User.roles.get_through_model(),
        User.approves_for.get_through_model()))
        
def drop_talbes():
    """
    Drop all model tables
    """
    models =  [User.roles.get_through_model(), User.approves_for.get_through_model()]
    models.extend(m for m in globals().values() if isinstance(m, type)  and issubclass(m, db.Model))
    drop_model_tables(models, fail_silently=True)
