import os, fnmatch
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from rooibos.storage.models import Storage
from rooibos.data.models import Collection
from rooibos.util import xfilter
from rooibos.access.models import ExtendedGroup, EVERYBODY_GROUP, AccessControl


def get_jmutube_storage():
    storage, created = Storage.objects.get_or_create(system='jmutube',
                                                     defaults=dict(title='JMUtube',
                                                                   base=settings.JMUTUBE_MEDIA_ROOT,
                                                                   name='jmutube'))
    if created:
        AccessControl.objects.create(content_object=storage, usergroup=get_jmutube_everybody_group(), read=True)
    return storage


def get_jmutube_collection():
    collection, created = Collection.objects.get_or_create(name='jmutube',
                                                           defaults=dict(title='JMUtube',
                                                                         description='JMUtube collection'))
    return collection


def get_jmutube_everybody_group():
    group, created = ExtendedGroup.objects.get_or_create(name='jmutube_everybody', type=EVERYBODY_GROUP)
    return group


def jmutube_login_required(function):
    decorator = login_required(function)
    decorator.login_url = settings.JMUTUBE_LOGIN_URL
    return decorator


def all_files(root, patterns='*', single_level=False, yield_folders=False):
    patterns = patterns.split(';')
    for path, subdir, files in os.walk(root):
        if yield_folders:
            files.extend(subdirs)
        files.sort()
        for name in files:
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    yield os.path.join(path, name)
                    break
        if single_level:
            break


def make_unique(filename):
    storage = get_jmutube_storage()
    pattern = '%s'.join(os.path.splitext(filename))
    for n in xrange(9999999):
        newname = pattern % ('(%s)' % n if n > 0 else '')
        if not storage.file_exists(newname):
            return newname
    raise Exception("Could not generate unique filename")


def sp_to_us(filename):
    return filename.replace(" ", "_")

def us_to_sp(filename):
    return filename.replace("_", " ")

def human_filesize(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
