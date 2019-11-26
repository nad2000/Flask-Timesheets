from datetime import datetime, timedelta
from peewee import (Model, CharField, DateTimeField, DeferredForeignKey, ForeignKeyField,
                    TextField, IntegerField, DateField, TimeField, BooleanField, ManyToManyField)
from . import (db, FlaskDB, app, current_user, current_week_ending_date, str_to_time)
from hashlib import md5
from flask_security import (PeeweeUserDatastore, UserMixin, RoleMixin, login_required)
from peewee import CompositeKey, RawQuery, OperationalError, ProgrammingError, DeferredThroughModel


class BaseModel(Model):
    """Application model base."""

    class Meta:  # noqa: D101,D106
        database = db
        only_save_dirty = True
        legacy_table_names = False


class Company(BaseModel):
    name = CharField()
    code = CharField()

    class Meta:
        table_alias = 'c'

    def __str__(self):
        return self.name


UserRoleDeferred = DeferredThroughModel()
ApproverCompanyDeferred = DeferredThroughModel()


class Role(BaseModel, RoleMixin):
    name = CharField(unique=True)
    description = TextField(null=True)

    class Meta:
        table_alias = 'r'



class User(BaseModel, UserMixin):
    username = CharField(unique=True, index=True)
    password = CharField()
    email = CharField()
    first_name = CharField()
    last_name = CharField()
    # confirmed_at = DateTimeField(null=True)
    active = BooleanField(default=True)
    workplace = ForeignKeyField(Company, backref='works_for')
    roles = ManyToManyField(Role, backref='users', through_model=UserRoleDeferred)
    approves_for = ManyToManyField(
        Company, backref='approved_by', through_model=ApproverCompanyDeferred)
    full_name = property(lambda self: "%s %s" % (self.first_name, self.last_name))

    def gravatar_url(self, size=80):
        return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % \
            (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)

    class Meta:
        order_by = ('username', )
        table_alias = 'u'

    def __str__(self):
        return self.full_name


class UserRole(BaseModel):
    user = ForeignKeyField(User, index=True)
    role = ForeignKeyField(Role, index=True)
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)

    class Meta:
        table_alias = 'ur'
        primary_key = CompositeKey('user', 'role')


UserRoleDeferred.set_model(UserRole)


class ApproverCompany(BaseModel):
    user = ForeignKeyField(User, index=True)
    company = ForeignKeyField(Company, index=True)
    name = property(lambda self: self.company.name)
    code = property(lambda self: self.company.code)

    class Meta:
        table_alias = "ac"
        primary_key = CompositeKey('user', 'company')


ApproverCompanyDeferred.set_model(ApproverCompany)


class Break(BaseModel):
    code = CharField(unique=True)
    name = CharField()
    minutes = IntegerField()
    alternative_code = CharField(unique=True, null=True)

    class Meta:
        order_by = ('code', )
        table_alias = 'b'

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Break(code=%r, name=%r, minutes=%r, alternative_code=%r)" \
            % (self.code, self.name, self.minutes, self.alternative_code)


class Entry(BaseModel):
    date = DateField()
    user = ForeignKeyField(User, backref='reported_by')
    approver = ForeignKeyField(User, backref='approved_by', null=True)
    started_at = TimeField()
    finished_at = TimeField()
    modified_at = DateTimeField(default=datetime.now)
    approved_at = DateTimeField(null=True)
    comment = TextField(null=True, default="")
    break_for = ForeignKeyField(Break, backref='break_for', null=True)
    is_approved = BooleanField(default=False)
    break_length = property(lambda self: self.break_for.minutes if self.break_for else 0)

    @property
    def total_min(self):
        if self.started_at is None or self.finished_at is None:
            return None
        total = (self.finished_at.hour - self.started_at.hour) * 60
        total += (self.finished_at.minute - self.started_at.minute)
        total -= self.break_length
        return total

    @property
    def total_time(self):
        total = self.total_min
        if total is None:
            return None
        return timedelta(hours=(total / 60), minutes=(total % 60))

    def __str__(self):
        output = "On %s from %s to %s" % (
            self.date.isoformat(), "N/A"
            if self.started_at is None else self.started_at.strftime("%H:%M"), "N/A"
            if self.finished_at is None else self.finished_at.strftime("%H:%M"))
        if self.break_for:
            output += " with beak for " + self.break_for.name

        total_min = self.total_min
        if total_min:
            output += ", total: %d:%02d" % (total_min // 60, total_min % 60)

        return output

    class Meta:
        table_alias = 'e'

    @classmethod
    def get_user_timesheet(cls, *, user=None, week_ending_date=None):
        """
        Retrievs timesheet entries for a user a week ending on week_ending_date.
        """
        if user is None:
            user = current_user

        if week_ending_date is None:
            week_ending_date = current_week_ending_date()

        rq = RawQuery(cls, """
        WITH
            daynums(num) AS (VALUES (6),(5),(4),(3),(2),(1),(0)),
            week(day) AS (SELECT date(?, '-'||num||' day') FROM daynums)
        SELECT
            id,
            day as date,
            finished_at,
            started_at,
            user_id,
            modified_at,
            break_for_id,
            is_approved,
            approver_id,
            approved_at,
            comment
        FROM week LEFT JOIN entry ON "date" = day AND user_id = ?
        ORDER BY "date" ASC""", week_ending_date.isoformat(), user.id)
        return rq.execute()

    @classmethod
    def get_for_approving(cls, *, user=None, week_ending_date=None):
        """
        Retrievs timesheet entries for approval
        """
        query = Entry.select()

        if user:
            query = query.where(Entry.user_id == user.id)

        if week_ending_date:
            week_start_date = week_ending_date - timedelta(days=7)
            query = query.where((Entry.date >= week_start_date) & (Entry.date <= week_ending_date))

        return query.order_by(Entry.date).limit(100).execute()


class TimeSheet:

    def __init__(self, *, user=None, week_ending_date=None):
        if user is None:
            user = current_user

        if week_ending_date is None:
            week_ending_date = current_week_ending_date()

        self.user = user
        self.week_ending_date = week_ending_date

        self.entries = Entry.get_user_timesheet(user=user, week_ending_date=week_ending_date)

    def update(self, rows):
        """
        Update timesheet entries or create new ones based on the submitted data
        based on the list of row values submitted by the user. rows - a list of
        dict of update data
        """
        for idx, (old, new) in enumerate(zip(self.entries, rows)):
            if not new["id"] or new["id"] == "None":
                if not new["started_at"] or new["started_at"] == "None" or not new[
                        "finished_at"] or new["finished_at"] == "None":  # Create a new entry
                    continue  # skip if there is no basic data

                old.user = User.get(id=current_user.id)
                row_date = self.week_ending_date - timedelta(days=(6 - idx))
                old.is_approved = False

            started_at = str_to_time(new["started_at"])
            finished_at = str_to_time(new["finished_at"])
            break_for = Break.get(id=int(new["break_id"])) if new["break_id"] else None

            if (old.started_at != started_at or old.finished_at != finished_at
                    or old.break_for != break_for):  # update only if there are changes:
                old.started_at = started_at
                old.finished_at = finished_at
                if break_for:
                    old.break_for = break_for
                old.modified_at = datetime.now()
                old.save()

    def approve(self, rows):
        """
        Approve timesheet entriesbased on the list of row values
        submitted by the user. rows - a list of dict of update data
        """
        for idx, (entry, row) in enumerate(zip(self.entries, rows)):

            if not entry.id:
                continue

            if "is_approved" in row:
                entry.is_approved = True
                entry.approver = current_user.id
                entry.comment = row["comment"]
                entry.approved_at = datetime.now()
            else:
                entry.is_approved = False
                entry.approver = None
                entry.comment = row["comment"]
                entry.approved_at = None

            entry.save()


# Setup Flask-Security
class UserDatastore(PeeweeUserDatastore):
    """Workaround for https://github.com/mattupstate/flask-security/issues/463"""

    def get_user(self, identifier):
        return self.user_model.get((self.user_model.id == identifier)
                                   | (self.user_model.username == identifier)
                                   | (self.user_model.email == identifier))


user_datastore = UserDatastore(db, User, Role, UserRole)

MODELS = [
    Company,
    Role,
    User,
    Break,
    Entry,
    UserRole,
    ApproverCompany,
]


def create_tables():
    """Create all DB tables"""
    if isinstance(db, FlaskDB):
        _db = db.database
    else:
        _db = db
    try:
        _db.connect()
    except OperationalError:
        pass

    for model in MODELS:

        try:
            model.create_table()
        except (ProgrammingError, OperationalError) as ex:
            if "already exists" in str(ex):
                app.logger.info(f"Table '{model._meta.name}' already exists")
            else:
                raise ex


def drop_talbes():
    """
    Drop all model tables
    """
    models = (m for m in globals().values() if isinstance(m, type) and issubclass(m, BaseModel))
    db.drop_tables(models, fail_silently=True)
