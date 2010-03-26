from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, HttpResponseForbidden
from django.core.files.uploadhandler import FileUploadHandler
from django.core.urlresolvers import reverse
from django.utils.http import urlencode
from django import forms
from django.contrib.auth.models import User
from django.conf import settings
import os
import re
import fnmatch
import shutil
from util import get_jmutube_storage, get_jmutube_uploaders_users_group, jmutube_login_required, all_files, make_unique
from jmutubestorage import determine_type, FILE_TYPES
from tagging.models import Tag, TaggedItem
from rooibos.data.models import Record, Field, FieldValue
from rooibos.util.models import OwnedWrapper
from rooibos.storage import get_thumbnail_for_record
from rooibos.ui import UploadProgressCachedHandler
from rooibos.access.views import login
import logging


def jmutube_login(request, *args, **kwargs):
    response = login(request, *args, **kwargs)
    if type(response) == HttpResponseRedirect:
        logging.debug("JMUtube login for %s" % request.user)
        get_jmutube_storage().storage_system.sync_files(request.user)
    return response



class RecordWrapper(object):

    #todo optimize queries
    def __init__(self, record):
        self.record = record
        self.id = record.id
        self.name = record.name
        self.title = record.title
        self.ownedwrapper = OwnedWrapper.objects.get_for_object(user=record.owner, object=record)
        media = record.media_set.select_related('storage').filter(master=None)
        if media:
            self.media = media[0]
            self.url = self.media.storage.storage_system.get_absolute_media_url(self.media.storage, self.media)
        else:
            self.media = None
            self.url = None


@jmutube_login_required
def media_main(request, type):
    
    if request.method == 'POST':
        tag = request.POST.get('tag').replace('"', '')
        ids = map(int, filter(None, request.POST.get('files').split(',')))
        if tag and ids:
            for record in Record.objects.filter(owner=request.user, source='jmutube-%s' % type, id__in=ids):
                Tag.objects.add_tag(OwnedWrapper.objects.get_for_object(user=record.owner, object=record),
                                    '"' + tag + '"')
        return HttpResponseRedirect(request.path + '?' + request.GET.urlencode())

    selected_tags = request.GET.getlist('tag')

    tag_url = request.path + "?"
    if selected_tags:
        tag_url += urlencode(('tag',t) for t in selected_tags) + "&"

    records = Record.objects.filter(owner=request.user, source='jmutube-%s' % type)

    if selected_tags:
        qs = OwnedWrapper.objects.filter(user=request.user,
                                         content_type=OwnedWrapper.t(Record),
                                         object_id__in=records)
        ids = list(TaggedItem.objects.get_by_model(qs, '"' + '","'.join(selected_tags) + '"').values_list('object_id', flat=True))
        records = Record.objects.filter(owner=request.user, id__in=ids)

    files = sorted(map(RecordWrapper, records), key=lambda r: r.title.lower())

    all_tags = filter(lambda t: t != 'JMUtube', (t.name for t in Tag.objects.usage_for_model(OwnedWrapper,
                    filters=dict(user=request.user,
                             content_type=OwnedWrapper.t(Record),
                             object_id__in=Record.objects.filter(owner=request.user, source='jmutube-%s' % type)))))


    tags = filter(lambda t: t not in selected_tags and t != 'JMUtube', (t.name for t in Tag.objects.usage_for_model(OwnedWrapper,
                    filters=dict(user=request.user,
                             content_type=OwnedWrapper.t(Record),
                             object_id__in=records))))


    return render_to_response(os.path.join('media', 'jmutube-%s.html' % type),
                              { 'type': type,
                               'files': files,
                               'tags': sorted(tags, key=lambda t:t.lower()),
                               'all_tags': sorted(all_tags, key=lambda t:t.lower()),
                               'tag_url': tag_url,
                               'selected_tags': sorted(selected_tags, key=lambda t:t.lower()),},
                              context_instance = RequestContext(request))



@jmutube_login_required
def migrate_files(request):
    path = os.path.join(settings.JMUTUBE_MEDIA_ROOT, request.user.username)

    if request.method == 'POST':
        for file in request.POST.getlist('file'):
            shutil.copy2(os.path.join(path, file), os.path.join(path, 'video'))
        get_jmutube_storage().storage_system.sync_files(request.user)
        return HttpResponseRedirect(reverse('jmutube-media', args=['video']))

    files = map(lambda f: {'name': os.path.split(f)[1],
                           'exists': os.path.exists(os.path.join(path, 'video', os.path.split(f)[1])) },
                filter(lambda f: os.path.split(f)[1][0] != ".",
                    all_files(path, patterns=';'.join(FILE_TYPES['video']), single_level=True)))

    return render_to_response('media/jmutube-migrate.html',
                              { 'files': files, 'path': path  },
                              context_instance = RequestContext(request))

@jmutube_login_required
def media_delete(request, type, id, name):
    record = get_object_or_404(Record,
                               owner=request.user,
                               source='jmutube-%s' % type,
                               id=id)

    if request.method == 'POST':
        for media in record.media_set.all():
            media.delete_file()
        record.delete()
        return HttpResponseRedirect(reverse('jmutube-media', args=[type]))

    return render_to_response("jmutube-confirm.html",
                              { 'message': 'Are you sure you want to delete the file "%s"?' % record.title, 'type': type },
                              context_instance = RequestContext(request))


class RenameForm(forms.Form):
    title = forms.CharField()

@jmutube_login_required
def media_rename(request, type, id, name):
    record = get_object_or_404(Record,
                           owner=request.user,
                           source='jmutube-%s' % type,
                           id=id)

    if request.method == 'POST':
        form = RenameForm(request.POST)
        if form.is_valid():
            fv = FieldValue.objects.get(record=record,
                                        field__name='title',
                                        field__standard__prefix='dc')
            fv.value = form.cleaned_data["title"]
            fv.save()
            return HttpResponseRedirect(reverse('jmutube-media', args=[type]))
    else:
        form = RenameForm(initial={'title': record.title})

    return render_to_response("jmutube-rename.html",
                              { 'form': form, 'type': type },
                              context_instance = RequestContext(request))


def thumbnail(request, username, id, name):
    record = get_object_or_404(Record, id=id, owner__username=username, source__startswith='jmutube')

    media = get_thumbnail_for_record(record, request.user, crop_to_square=request.GET.has_key('square'))
    if media:
        content = media.load_file()
        if content:
            return HttpResponse(content=content, mimetype=str(media.mimetype))
        else:
            return HttpResponseServerError()
    else:
        return HttpResponseRedirect(reverse('jmutube-static', args=('images/nothumbnail.jpg',)))


@jmutube_login_required
def upload_file(request):

    uploader = request.user.is_superuser or request.user.groups.filter(id=get_jmutube_uploaders_users_group().id).count() > 0
    if uploader:
        available_users = User.objects.filter(is_active=True).order_by('username').values_list('id', 'username')
    else:
        available_users = [(request.user.id, request.user.username)]

    class UploadFileForm(forms.Form):
        file = forms.FileField(label="Upload new file")
        tag = forms.CharField(label="Tag uploads with:", required=False)
        for_user = forms.ChoiceField(label="Target user:", choices=((i, u) for i, u in available_users), required=False)


    if request.method == 'POST':
#        request.upload_handlers.insert(0, UploadProgressCachedHandler(request, 1024 ** 3)) # limit upload to 1 GB
        uploadform = UploadFileForm(request.POST, request.FILES)
        if uploadform.is_valid():
            if uploader and int(uploadform.cleaned_data.get('for_user', 0)) in (i for i, u in available_users):
                target_user = User.objects.get(id=uploadform.cleaned_data['for_user'])
            else:
                target_user = request.user
            file = request.FILES['file']
            type = determine_type(file.name)
            tag = uploadform.cleaned_data.get('tag')
            if type:
                storage = get_jmutube_storage()
                base, ext = os.path.splitext(file.name)
                name = make_unique(os.path.join(target_user.username, type, re.sub(r'[^\w]+', '_', base) + ext.lower()))
                storage.save_file(name, file)
                record = storage.storage_system.create_record_for_file(target_user, name, type)
                if tag:
                    wrapper = OwnedWrapper.objects.get_for_object(user=record.owner, object=record)
                    Tag.objects.add_tag(wrapper, '"' + tag + '"')

                if request.POST.get('swfupload') == 'true':
                    return HttpResponse(content='ok', mimetype='text/plain')

                return HttpResponseRedirect(reverse('jmutube-media', args=[type]))
            else:
                if request.POST.get('swfupload') == 'true':
                    return HttpResponseForbidden(content='invalid type', mimetype='text/plain')
                
                request.user.message_set.create(message="The file you uploaded does not have a valid extension." +
                                                "Valid files are %s." % (','.join(filter(None, [','.join(x) for x in FILE_TYPES.values()]))))
                return HttpResponseRedirect(reverse('jmutube-upload'))
    else:
        uploadform = UploadFileForm(initial={'for_user': request.user.id})

    return render_to_response('jmutube-upload.html',
                              { 'form': uploadform,
                                'uploader': uploader,
                                },
                              context_instance=RequestContext(request))
