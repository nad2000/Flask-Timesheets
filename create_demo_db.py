#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask_timesheets import bcrypt
from models import *

# remove sqlite DB:
if isinstance(db, FlaskDB):
    _db = db.database
else:
    _db = db
    
if os.path.exists(_db.database):
    try:
        os.remove(_db.database)
    except:  ## if fails, drop all model tables:
        drop_talbes()
    
# create all tales from the scratch:
create_tables()

# Create all roles:
emp = Role.insert(name="emp").execute()
approver = Role.insert(name="approver").execute()
admin = Role.insert(name="admin").execute()

# Companies:
Company.insert_many((dict(code=code, name=name) for code, name in (
    ('Z4M4Q0','Hoofs and horns Ltd.'),
    ('B4J4L6','Acme Ltd.'),
    ('Y9P9S3','Viral Marvels Ltd.'),
    ('V9A5K4','Happy Feets Ltd.'),
    ('Y0U5B3','Abra Cadabra Ltd.'),
    ('T3N2Y6','No Need Ltd.'),
    ('Q6U3Y9','Nullam vitae Ltd.'),
    ('W9J2M9','Ipsum Ltd.'),
    ('Y3Z9T9','Suspendisse Sagittis Ltd.'),
    ('R2H4P5','Nulla Ltd.'),
))).execute()

# Users;
test_password = bcrypt.generate_password_hash('12345')
for id, (username, email, first_name, last_name) in enumerate((
            ('user0', 'user0@nowhere.com','Test', 'User0'),
            ('user1', 'user1@nowhere.com','Test', 'User1'),
            ('user2', 'user2@nowhere.com','Test', 'User2'),
            ('admin0', 'admin0@nowhere.com','Test', 'Admin0'),
            ('admin1', 'admin1@nowhere.com','Test', 'Admin1'),
            ('admin2', 'admin2@nowhere.com','Test', 'Admin2'),), 1):
    user = User(
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
    elif "admin" in username:
        user.roles = [admin, approver]
    else:
        user.roles = [approver]
        
    user.save()
