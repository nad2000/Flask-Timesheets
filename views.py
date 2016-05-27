from flask_timesheets import app, db
from flask import g, render_template, redirect, flash, url_for, session, abort, request
from models import User, Company, Break
from peewee import IntegrityError
from functools import wraps
from datetime import datetime
from hashlib import md5


def auth_user(user):
    """
    this function allows us to mark a user as being logged-in by setting some values in the session data
    """
    session['logged_in'] = True
    session['user_id'] = user.id
    session['username'] = user.username
    flash('You are logged in as %s' % (user.username))


def get_current_user():
    """
    get the user from the session
    """
    if session.get('logged_in'):
        return User.get(User.id == session['user_id'])

# view decorator which indicates that the requesting user must be authenticated
# before they can access the view.  it checks the session to see if they're
# logged in, and if not redirects them to the login view.
def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('twitter_login'))
        return f(*args, **kwargs)
    return inner

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

# custom template filter -- flask allows you to define these functions and then
# they are accessible in the template -- this one returns a boolean whether the
# given user is following another user.
@app.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)


# views -- these are the actual mappings of url to view function
@app.route('/')
def homepage():
    # depending on whether the requesting user is logged in or not, show them
    # either the public timeline or their own private timeline
    if session.get('logged_in'):
        ## TODO: redirect to the last visited page
        return private_timeline()
    else:
        pass ## TODO:
        #return login()
    return render_template("empty.html")


@app.route("/timesheet/<date:week_start_date>")
@app.route("/timesheet/")    
def timesheet(week_start_date=None):
    # TODO: handle dates
    return render_template("timesheet.html")

    
@app.route("/approve/<user_name>/<date:week_start_date>")
@app.route("/approve/<user_name>")
@app.route("/approve/")
# TODO: approver role
def approve(user_name=None, week_start_date=None):
    # TODO: handle dates
    return render_template("approve.html")


@app.route('/private/')
def private_timeline():
    # the private timeline exemplifies the use of a subquery -- we are asking for
    # messages where the person who created the message is someone the current
    # user is following.  these messages are then ordered newest-first.
    user = get_current_user()
    messages = Message.select().where(Message.user << user.following())
    return object_list('private_messages.html', messages, 'message_list')

@app.route('/public/')
def public_timeline():
    # simply display all messages, newest first
    messages = Message.select()
    return object_list('public_messages.html', messages, 'message_list')

@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST' and request.form['username']:
        try:
            with db.transaction():
                # Attempt to create the user. If the username is taken, due to the
                # unique constraint, the database will raise an IntegrityError.
                user = User.create(
                    username=request.form['username'],
                    password=md5((request.form['password']).encode('utf-8')).hexdigest(),
                    email=request.form['email'],
                    join_date=datetime.now())

            # mark the user as being 'authenticated' by setting the session vars
            auth_user(user)
            return redirect(url_for('homepage'))

        except IntegrityError:
            flash('That username is already taken')

    return render_template('join.html')

@app.route('/login/', methods=['GET', 'POST'])
def twitter_login():
    """
    twitter_login so that it doesn't clash with blog's login
    """
    if request.method == 'POST' and request.form['username']:
        try:
            user = User.get(
                username=request.form['username'],
                password=md5((request.form['password']).encode('utf-8')).hexdigest())
        except User.DoesNotExist:
            flash('The password entered is incorrect')
        else:
            auth_user(user)
            return redirect(url_for('homepage'))

    return render_template('login.html')

@app.route('/logout/')
def twitter_logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('homepage'))

@app.route('/following/')
@login_required
def following():
    user = get_current_user()
    return object_list('user_following.html', user.following(), 'user_list')

@app.route('/followers/')
@login_required
def followers():
    user = get_current_user()
    return object_list('user_followers.html', user.followers(), 'user_list')

@app.route('/users/')
def user_list():
    users = User.select()
    return object_list('user_list.html', users, 'user_list')

@app.route('/users/<username>/')
def user_detail(username):
    # using the "get_object_or_404" shortcut here to get a user with a valid
    # username or short-circuit and display a 404 if no user exists in the db
    user = get_object_or_404(User, User.username == username)

    # get all the users messages ordered newest-first -- note how we're accessing
    # the messages -- user.message_set.  could also have written it as:
    # Message.select().where(user=user).order_by(('pub_date', 'desc'))
    messages = user.message_set
    return object_list('user_detail.html', messages, 'message_list', user=user)

@app.route('/users/<username>/follow/', methods=['POST'])
@login_required
def user_follow(username):
    user = get_object_or_404(User, User.username == username)
    try:
        with db.transaction():
            Relationship.create(
                from_user=get_current_user(),
                to_user=user)
    except IntegrityError:
        pass

    flash('You are following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/users/<username>/unfollow/', methods=['POST'])
@login_required
def user_unfollow(username):
    user = get_object_or_404(User, User.username == username)
    Relationship.delete().where(
        (Relationship.from_user == get_current_user()) &
        (Relationship.to_user == user)
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/create/', methods=['GET', 'POST'])
@login_required
def create():
    user = get_current_user()
    if request.method == 'POST' and request.form['content']:
        message = Message.create(
            user=user,
            content=request.form['content'],
            pub_date=datetime.now())
        flash('Your message has been created')
        return redirect(url_for('user_detail', username=user.username))

    return render_template('create.html')

@app.context_processor
def _inject_user():
    return {'current_user': get_current_user()}
    
