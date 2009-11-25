
#ROOT_URLCONF = 'apps.jmutube.urls'
#JMUTUBE_LOGIN_URL = '/accounts/login/'

JMUTUBE_LOGIN_URL = '/jmutube/accounts/login/'


# Path information

JMUTUBE_STATIC_FILES          = 'd:/dev/rooibos/apps/jmutube/static'
JMUTUBE_MEDIA_ROOT            = 'd:/dev/jmutube/media'
JMUTUBE_CRASS_MISC_FOLDER     = 'd:/dev/jmutube/media/misc'
JMUTUBE_RELAY_INCOMING_FOLDER = 'd:/dev/jmutube/media/relay_incoming'


# Don't need to change anything below this line

# append additional apps
INSTALLED_APPS = (
    'apps.jmutube',
    'apps.jmutube.repository',
    'apps.jmutube.crass',
    'apps.jmutube.relay',
)

# append JMUtube storage system
STORAGE_SYSTEMS = {
    'jmutube': 'apps.jmutube.jmutubestorage.JMUtubeStorageSystem',
}


# restrict to users with certain attributes
JMUTUBE_USER_RESTRICTION = { 'eduPersonPrimaryAffiliation': ('faculty', 'staff', 'administrator') }
