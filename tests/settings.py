# Django settings for testproject project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#         'NAME': 'pydjango',                      # Or path to database file if using sqlite3.
#         'USER': 'krya',                      # Not used with sqlite3.
#         'PASSWORD': '666',                  # Not used with sqlite3.
#         'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
#         'PORT': '5432',                      # Set to empty string for default. Not used with sqlite3.
#     }
# }

SITE_ID = 1

# Make this unique, and don't share it with anybody.
SECRET_KEY = '*_1cc9n+lc@l$#hmd-)#(@0-i=@jbzb2zkmbv8nvf)qodq37^l'



ROOT_URLCONF = 'tests.urls'


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
)
