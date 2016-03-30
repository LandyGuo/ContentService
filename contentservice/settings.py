# Django settings for server project.
import os, re
from ConfigParser import SafeConfigParser

from contentservice.utils import rdb
rdb.listen()

DEBUG = False
TEMPLATE_DEBUG = DEBUG

SRC_PATH = os.path.dirname(os.path.dirname(__file__))
LOGGERS_NAME = ["contentservice",
                "contentimport",
                "contentcrawler",
                "api", 
                "api_ring", 
                "api_novel", 
                "api_video", 
                "api_admin", 
                "inserted_video", 
                "updated_video", 
                "skipped_video"]

LOG_BASE = '/var/app/log/contentservice'
DATA_BASE = '/var/app/data/contentservice'

STATIC_BASE = "/vol1/www"
STATIC_SERVER = "static.55yule.com"

RING_SERVER = "ring.dianapk.qihang.us"

MONGO_CONN_STR = None
MQ_CONF = None

CRAWLER_PID = "/var/run/contentcrawler.pid"
CRAWLER_PROCESS_MAX_TIME = 3600
CRAWLER_TIMEOUT_DEFAULT = 3600
DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; U; Android 2.3.3; zh-tw; HTC_Pyramid Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1' }

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Asia/Shanghai'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '27*8)rm(yo^gxy30_7k41hgdnr58q2g+b_r#fhp&amp;+xmllajkpu'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
#    'django.middleware.common.CommonMiddleware',
     'contentservice.middlewares.UnproxyMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
)
#
# TEMPLATE_CONTEXT_PROCESSORS = (
#    'django.contrib.messages.context_processors.messages',
#    'django.contrib.auth.context_processors.auth',
# )

ROOT_URLCONF = 'contentservice.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'contentservice.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'contentservice',
#    'django.contrib.auth',
#    'django.contrib.contenttypes',
#    'django.contrib.messages',
#    'django.contrib.sessions',
#    'django.contrib.admin',
)


def _load_config():
    global DEBUG, TEMPLATE_DEBUG, LOG_BASE, DATA_BASE
    global MONGO_CONN_STR, MQ_CONF

    SECTION = 'contentservice'

    cp = SafeConfigParser()
    cp.read(os.path.join(SRC_PATH, "contentservice.cfg"))

    DEBUG = cp.getboolean(SECTION, 'debug')
    TEMPLATE_DEBUG = DEBUG

    LOG_BASE = cp.get(SECTION, 'logs_dir')
    DATA_BASE = cp.get(SECTION, 'data_dir')

    # mongo
    MONGO_CONN_STR = cp.get(SECTION, 'mongo_conn_str')
    mq_conn_str = cp.get(SECTION, 'mq_conn_str')

    MQ_CONF = re.match(r"amqp://(?P<user>.+):(?P<password>.+)@(?P<host>.+):(?P<port>\d+)/(?P<vhost>.+)", mq_conn_str).groupdict()


def get_logging(loggers_name):
    logging = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(levelname)s\t%(asctime)s\t%(message)s'
            },
            'detail': {
                'format': '%(levelname)s\t%(asctime)s\t[%(module)s.%(funcName)s line:%(lineno)d]\t%(message)s',
            },
         }
        }
    handlers = {
            }
    loggers = {}

    for logger_name in loggers_name:
        handlers[logger_name + "_file"] = {
            'level': 'DEBUG',
            'formatter': 'detail',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(LOG_BASE, logger_name + ".log"),
         }
        handlers[logger_name + "_err_file"] = {
            'level': 'WARN',
            'formatter': 'detail',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(LOG_BASE, logger_name + "_error.log"),
        }
        loggers[logger_name]  = {
            'handlers': [logger_name + '_file',  logger_name +'_err_file'],
            'level': 'DEBUG',
            'propagate': True,
        }

    logging['handlers'] = handlers
    logging['loggers'] = loggers

    return logging

_load_config()
LOGGING = get_logging(LOGGERS_NAME)
