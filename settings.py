import os

SECRET_KEY = 'p3-9ug8e6jyg%j-)4n36yethsthdud705k#5=86w=x&4mizw89'
DEBUG = True
DATABASE = "sqlite:///timesheet.db"

DEBUG_TB_INTERCEPT_REDIRECTS = False


# Flask-Security config
###SECURITY_URL_PREFIX = "/admin"
SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = "hd$Td70F5k#5=8"
# login with a username or an email address
SECURITY_USER_IDENTITY_ATTRIBUTES = ('username','email')

# Flask-Security URLs, overridden because they don't put a / at the end
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"
SECURITY_REGISTER_URL = "/register/"

#SECURITY_POST_LOGIN_VIEW = "/admin/"
#SECURITY_POST_LOGOUT_VIEW = "/admin/"
#SECURITY_POST_REGISTER_VIEW = "/admin/"

# Flask-Security features
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
