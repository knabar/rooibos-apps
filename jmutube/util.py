import os, fnmatch
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from rooibos.storage.models import Storage
from rooibos.data.models import Collection
from rooibos.util import xfilter
from rooibos.access.models import ExtendedGroup, EVERYBODY_GROUP, ATTRIBUTE_BASED_GROUP, AccessControl


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


def get_jmutube_allowed_users_group():
    group, created = Group.objects.get_or_create(name='jmutube_allowed_users')
    return group


def get_jmutube_facultystaff_group():
    if not hasattr(settings, 'JMUTUBE_USER_RESTRICTION'):
        return None
    group, created = ExtendedGroup.objects.get_or_create(name='jmutube_facultystaff', type=ATTRIBUTE_BASED_GROUP)
    if created:
        for attr in settings.JMUTUBE_USER_RESTRICTION.keys():
            attribute = group.attribute_set.create(attribute=attr)
            for val in settings.JMUTUBE_USER_RESTRICTION[attr]:
                attribute.attributevalue_set.create(value=val)
    return group


def jmutube_login_required(function, redirect_field_name=REDIRECT_FIELD_NAME):
    def _is_authenticated(user):
        if not user.is_authenticated():
            return False
        if user.is_superuser:
            return True
        group = get_jmutube_facultystaff_group()
        if group and (group.user_set.filter(id=user.id).count() == 1):
            return True
        group = get_jmutube_allowed_users_group()
        if group and (group.user_set.filter(id=user.id).count() == 1):
            return True
        return False
    actual_decorator = user_passes_test(
        _is_authenticated,
        redirect_field_name=redirect_field_name
    )
    actual_decorator = actual_decorator(function)
    actual_decorator.login_url = settings.JMUTUBE_LOGIN_URL
    return actual_decorator


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
