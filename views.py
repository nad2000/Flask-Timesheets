from flask_timesheets import app, db, admin, ModelView, current_user, current_week_ending_date, week_ending_dates, timedelta
from flask import g, render_template, redirect, flash, url_for, session, abort, request
from models import User, Role, Company, Break, Entry, user_datastore
from peewee import IntegrityError
from functools import wraps
from datetime import datetime
from hashlib import md5
from flask.ext.security import login_required, roles_required, Security
from forms import ExtendedLoginForm, TimeSheetForm

security = Security(app, user_datastore, login_form=ExtendedLoginForm)

def str_to_date(str):
    return datetime.strptime(str, '%Y-%m-%d').date()

def str_to_time(str):
    return datetime.strptime(str, '%H:%M').time()
    
    
class AppModelView(ModelView):
    """
    Admin Model view customization according to
    """

    column_formatters = dict(
        started_at=lambda v, c, m, p: m.started_at.strftime("%H:%M"),
        finished_at=lambda v, c, m, p: m.finished_at.strftime("%H:%M"),
        modified_at=lambda v, c, m, p: m.modified_at.strftime("%Y-%m-%d %H:%M"),
    )

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class UserView(AppModelView):
    can_create = False
    column_exclude_list = ['password']

admin.add_view(AppModelView(Break))
admin.add_view(UserView(User))
admin.add_view(AppModelView(Role))
admin.add_view(AppModelView(Company))
admin.add_view(AppModelView(Entry))


# given a template and a SelectQuery instance, render a paginated list of
# objects from the query inside the template
def object_list(template_name, qr, var_name='object_list', **kwargs):
    kwargs.update(
        page=int(request.args.get('page', 1)),
        pages=qr.count() / 20 + 1
    )
    kwargs[var_name] = qr.paginate(kwargs['page'])
    return render_template(template_name, **kwargs)

    
# retrieve a single object matching the specified query or 404 -- this uses the
# shortcut "get" method on model, which retrieves a single object or raises a
# DoesNotExist exception if no matching object exists
# http://charlesleifer.com/docs/peewee/peewee/models.html#Model.get)
def get_object_or_404(model, *expressions):
    try:
        return model.get(*expressions)
    except model.DoesNotExist:
        abort(404)
        

@app.template_filter('total_time')
def total_time(entry):
    """
    textual representation of total work time
    """
    total_min = entry.total_min
    if total_min:
        return "%d:%02d" % (total_min // 60, total_min % 60)


@app.template_filter('hhmm')
def hhmm(time):
    """
    textual representation of time in format HH:MM
    """
    return time.strftime("%H:%M") if time else ''
        
        
# views -- these are the actual mappings of url to view function
@app.route('/')
@login_required
def homepage():
    return render_template("empty.html")

    
@app.route("/timesheet/<date:week_ending_date>", methods=["GET", "POST"])
@app.route("/timesheet/", methods=["GET", "POST"])    
@login_required
def timesheet(week_ending_date=None):
    if week_ending_date is None:
        week_ending_date = current_week_ending_date()
      
    breaks = Break.select(Break.id, Break.name).execute()
    
    form = TimeSheetForm()
    
    if form.validate_on_submit():
        for row_idx in range(7):
            row = {k.split(':')[1]: request.form[k] for k in request.form.keys() if k.startswith("%d:" % row_idx)}
            if row["id"] and row["id"] != "None":  ## Update the row
                entry = Entry.get(id=int(row["id"]))
                entry.started_at=str_to_time(row["started_at"])
                entry.finished_at=str_to_time(row["finished_at"])
                entry.break_for=Break.get(id=int(row["break_id"])) if row["break_id"] else None
                entry.save()
            elif row["started_at"] and row["started_at"] != "None" and row["finished_at"] and row["finished_at"] != "None":  ## Create a new entry
                row_date = week_ending_date - timedelta(days=(6-row_idx))
                entry = Entry(
                    date=row_date,
                    user=User.get(id=current_user.id),
                    started_at=str_to_time(row["started_at"]),
                    finished_at=str_to_time(row["finished_at"]),
                    break_for=Break.get(id=int(row["break_id"])) if row["break_id"] else None
                )
                entry.save()
    
    timesheet = Entry.get_user_timesheet(
        user=current_user, 
        week_ending_date=week_ending_date)
    
    return render_template("timesheet.html",
        timesheet=timesheet,
        form=form,
        breaks=breaks,
        week_ending_date=week_ending_date, 
        week_ending_dates=week_ending_dates())
        
    
    
@app.route("/approve/<user_name>/<date:week_ending_date>")
@app.route("/approve/<user_name>")
@app.route("/approve/")
@login_required
@roles_required('approver')
def approve(user_name=None, week_ending_date=None):
    # TODO: handle dates
    return render_template("approve.html")

@app.route("/report/<user_name>/<date:week_ending_date>")
@app.route("/report/<user_name>")
@app.route("/report/")
@login_required
@roles_required('approver')
def report(user_name=None, week_ending_date=None):
    # TODO: handle dates
    return render_template("empty.html")


# @app.route('/private/')
# @login_required
# def private_timeline():
    # # the private timeline exemplifies the use of a subquery -- we are asking for
    # # messages where the person who created the message is someone the current
    # # user is following.  these messages are then ordered newest-first.
    # user = get_current_user()
    # messages = Message.select().where(Message.user << user.following())
    # return object_list('private_messages.html', messages, 'message_list')

# @app.route('/public/')
# def public_timeline():
    # # simply display all messages, newest first
    # messages = Message.select()
    # return object_list('public_messages.html', messages, 'message_list')

# @app.route('/join/', methods=['GET', 'POST'])
# def join():
    # if request.method == 'POST' and request.form['username']:
        # try:
            # with db.transaction():
                # # Attempt to create the user. If the username is taken, due to the
                # # unique constraint, the database will raise an IntegrityError.
                # user = User.create(
                    # username=request.form['username'],
                    # password=md5((request.form['password']).encode('utf-8')).hexdigest(),
                    # email=request.form['email'],
                    # join_date=datetime.now())

            # # mark the user as being 'authenticated' by setting the session vars
            # auth_user(user)
            # return redirect(url_for('homepage'))

        # except IntegrityError:
            # flash('That username is already taken')

    # return render_template('join.html')

# @app.route('/login/', methods=['GET', 'POST'])
# def twitter_login():
    # """
    # twitter_login so that it doesn't clash with blog's login
    # """
    # if request.method == 'POST' and request.form['username']:
        # try:
            # user = User.get(
                # username=request.form['username'],
                # password=md5((request.form['password']).encode('utf-8')).hexdigest())
        # except User.DoesNotExist:
            # flash('The password entered is incorrect')
        # else:
            # auth_user(user)
            # return redirect(url_for('homepage'))

    # return render_template('login.html')

# @app.route('/logout/')
# def twitter_logout():
    # session.pop('logged_in', None)
    # flash('You were logged out')
    # return redirect(url_for('homepage'))

# @app.route('/following/')
# @login_required
# def following():
    # user = get_current_user()
    # return object_list('user_following.html', user.following(), 'user_list')

# @app.route('/followers/')
# @login_required
# def followers():
    # user = get_current_user()
    # return object_list('user_followers.html', user.followers(), 'user_list')

# @app.route('/users/')
# def user_list():
    # users = User.select()
    # return object_list('user_list.html', users, 'user_list')

# @app.route('/users/<username>/')
# def user_detail(username):
    # # using the "get_object_or_404" shortcut here to get a user with a valid
    # # username or short-circuit and display a 404 if no user exists in the db
    # user = get_object_or_404(User, User.username == username)

    # # get all the users messages ordered newest-first -- note how we're accessing
    # # the messages -- user.message_set.  could also have written it as:
    # # Message.select().where(user=user).order_by(('pub_date', 'desc'))
    # messages = user.message_set
    # return object_list('user_detail.html', messages, 'message_list', user=user)

# @app.route('/users/<username>/follow/', methods=['POST'])
# @login_required
# def user_follow(username):
    # user = get_object_or_404(User, User.username == username)
    # try:
        # with db.transaction():
            # Relationship.create(
                # from_user=get_current_user(),
                # to_user=user)
    # except IntegrityError:
        # pass

    # flash('You are following %s' % user.username)
    # return redirect(url_for('user_detail', username=user.username))

# @app.route('/users/<username>/unfollow/', methods=['POST'])
# @login_required
# def user_unfollow(username):
    # user = get_object_or_404(User, User.username == username)
    # Relationship.delete().where(
        # (Relationship.from_user == get_current_user()) &
        # (Relationship.to_user == user)
    # ).execute()
    # flash('You are no longer following %s' % user.username)
    # return redirect(url_for('user_detail', username=user.username))

# @app.route('/create/', methods=['GET', 'POST'])
# @login_required
# def create():
    # user = get_current_user()
    # if request.method == 'POST' and request.form['content']:
        # message = Message.create(
            # user=user,
            # content=request.form['content'],
            # pub_date=datetime.now())
        # flash('Your message has been created')
        # return redirect(url_for('user_detail', username=user.username))

    # return render_template('create.html')

# @app.context_processor
# def _inject_user():
    # return {'current_user': get_current_user()}
    
