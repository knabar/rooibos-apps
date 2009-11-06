import os, fnmatch
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from rooibos.storage.models import Storage
from rooibos.data.models import Collection
from rooibos.util import xfilter
from rooibos.access.models import ExtendedGroup, EVERYBODY_GROUP, AccessControl


def get_svohp_storage():
    storage, created = Storage.objects.get_or_create(system='local',
                                                     name='svohp',
                                                     defaults=dict(title='SVOHP',
                                                                   base=settings.SVOHP_MEDIA_ROOT))
    if created:
        AccessControl.objects.create(content_object=storage, usergroup=get_svohp_everybody_group(), read=True)
    return storage


def get_svohp_collection():
    collection, created = Collection.objects.get_or_create(name='svohp',
                                                           defaults=dict(title='Shenandoah Valley Oral History Project',
                                                                         description='The Shenandoah Valley Oral History Project seeks to document the lives of people throughout the Valley whose stories have largely gone untold.'))
    if created:
        AccessControl.objects.create(content_object=collection, usergroup=get_svohp_everybody_group(), read=True)
    return collection


def get_svohp_everybody_group():
    group, created = ExtendedGroup.objects.get_or_create(name='svohp_everybody', type=EVERYBODY_GROUP)
    return group

