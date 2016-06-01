from datetime import datetime
from peewee import Model, CharField, DateTimeField, ForeignKeyField, \
    TextField, IntegerField, DateField, TimeField, BooleanField
from flask_timesheets import db, FlaskDB, app, current_user, current_week_ending_date
from hashlib import md5
from flask.ext.security import Security, PeeweeUserDatastore, UserMixin, \
    RoleMixin, login_required
from playhouse.fields import ManyToManyField
from peewee import drop_model_tables, Proxy, CompositeKey, RawQuery
from forms import ExtendedLoginForm

UserRolesProxy = Proxy()
ApproverCompaniesProxy = Proxy()

class Company(db.Model):
    name = CharField()
    code = CharField()
    
    class Meta:
        table_alias = 'c'
        
    def __str__(self):
        return self.name
      
    
class Role(db.Model, RoleMixin):
    name = CharField(unique=True)
    description = TextField(null=True)
    
    class Meta:
        table_alias = 'r'
    
class User(db.Model, UserMixin):
    username = CharField(unique=True, index=True)
    password = CharField()
    email = CharField()
    first_name = CharField()
    last_name = CharField()
    #confirmed_at = DateTimeField(null=True)
    active = BooleanField(default=True)
    workplace = ForeignKeyField(Company, related_name='works_for')
    roles = ManyToManyField(Role, related_name='users', through_model=UserRolesProxy)
    approves_for = ManyToManyField(Company, related_name='approved_by', through_model=ApproverCompaniesProxy)
    full_name = property(lambda self: "%s %s" % (self.first_name, self.last_name))

    def gravatar_url(self, size=80):
        return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % \
            (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)
    
    class Meta:
        order_by = ('username',)
        table_alias = 'u'
        
    def __str__(self):
        return self.full_name

class UserRoles(db.Model):
    user = ForeignKeyField(User, index=True, db_column='user_id')
    role = ForeignKeyField(Role, index=True, db_column='role_id')
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)
    
    class Meta:
        db_table = "user_role"
        table_alias = 'ur'
        primary_key = CompositeKey('user', 'role')

UserRolesProxy.initialize(UserRoles)
 
class ApproverCompanies(db.Model):
    user = ForeignKeyField(User, index=True, db_column='user_id')
    company = ForeignKeyField(Company, index=True, db_column='company_id')
    name = property(lambda self: self.company.name)
    code = property(lambda self: self.company.code)

    class Meta:
        db_table = "approver_company"
        table_alias = "ac"
        primary_key = CompositeKey('user', 'company')
            
ApproverCompaniesProxy.initialize(ApproverCompanies)

class Break(db.Model):
    code = CharField(unique=True)
    name = CharField()
    minutes = IntegerField()
    alternative_code = CharField(unique=True, null=True)

    class Meta:
        order_by = ('code',)
        table_alias = 'b'
    
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
    break_length = property(lambda self: self.break_for.minutes if self.break_for else 0)
    
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

    class Meta:
        table_alias = 'e'

    @classmethod
    def get_user_timesheet(cls, *, user=None, week_ending_date=None):
        if user is None:
            user = current_user
            
        if week_ending_date is None:
            week_ending_date = current_week_ending_date()
            
        rq = RawQuery(cls, """
        WITH
            daynums(num) AS (VALUES (6),(5),(4),(3),(2),(1),(0)),
            week(day) AS (SELECT date(?, '+'||num||' day')FROM daynums)
        SELECT
            id,
            day as date,
            finished_at,
            started_at,
            user_id,
            approver_id,
            modified_at,
            break_for_id,
            is_approved,
            comment
        FROM week LEFT JOIN entry ON "date" = day AND user_id = ?
        ORDER BY "date" ASC""", week_ending_date.isoformat(), user.id)
        return rq.execute()

        
# Setup Flask-Security
user_datastore = PeeweeUserDatastore(db, User, Role, UserRoles)
security = Security(app, user_datastore, login_form=ExtendedLoginForm)
        
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
        UserRoles,
        ApproverCompanies,))
 
 
def drop_talbes():
    """
    Drop all model tables
    """
    models = (m for m in globals().values() if isinstance(m, type)  and issubclass(m, db.Model))
    drop_model_tables(models, fail_silently=True)
