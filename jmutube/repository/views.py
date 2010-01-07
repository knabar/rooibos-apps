from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib.auth.models import User
from apps.jmutube.util import *
from tagging.models import Tag, TaggedItem
from rooibos.util import json_view
from rooibos.data.models import Record
from rooibos.util.models import OwnedWrapper
from rooibos.presentation.models import Presentation, PresentationItem, PresentationItemInfo


def playlist_rss_feed(request, user, title):
    playlist = get_object_or_404(Presentation,
                                 Q(name=title) | Q(id=title),
                                 owner__username=user,
                                 source='jmutube')
    storage = get_jmutube_storage()

    def items():
        for item in playlist.items.all():
            media = item.record.media_set.filter(storage=storage)[0]
            yield item.record, media, item.type

    return render_to_response('jmutube-playlist.rss',
                              { 'title': playlist.title,
                               'user': playlist.owner,
                               'url': 'http://jmutube.cit.jmu.edu/',
                               'jmutube_player': request.GET.get('player') == 'jmutube',
                               'playlist': (
                                    {'file': record,
                                     'url': storage.storage_system.get_absolute_media_url(storage, media, delivery),
                                     'jmutube_player_url': storage.storage_system.get_jmutube_player_url(storage, media, delivery),
                                     'mimetype': media.mimetype,
                                     'size': media.file_size,
                                }
                                for record, media, delivery in items() )},
                              context_instance = RequestContext(request))

def single_file_rss_feed(request, user, id, name):
    storage = get_jmutube_storage()
    user = User.objects.get(username=user)
    record = get_object_or_404(Record,
                       owner=user,
                       source__startswith='jmutube-',
                       id=id)
    media = record.media_set.filter(storage=storage)[0]
    jmutube_player = request.GET.get('player') == 'jmutube'

    return render_to_response('jmutube-playlist.rss',
                              { 'title': record.title,
                               'user': user,
                               'url': 'http://jmutube.cit.jmu.edu/',
                               'jmutube_player': jmutube_player,
                               'playlist': ({'file': record,
                                             'url': storage.storage_system.get_absolute_media_url(storage, media),
                                             'jmutube_player_url': storage.storage_system.get_jmutube_player_url(storage, media),
                                             'mimetype': media.mimetype,
                                             'size': media.file_size,
                                             },) },
                              context_instance = RequestContext(request))

def playlist_play(request, user, title):
    playlist = get_object_or_404(Presentation,
                                 Q(name=title) | Q(id=title),
                                 owner__username=user,
                                 source='jmutube')
    return render_to_response('jmutube-playlist.html',
                              { 'title': playlist.title,
                                'feed': 'http://%s%s' % (request.get_host(), reverse('jmutube-playlist-rss-feed', args=(user, playlist.id))) },
                              context_instance = RequestContext(request))

def playlist_download(request, user, title):
    playlist = get_object_or_404(Presentation,
                                 Q(name=title) | Q(id=title),
                                 owner__username=user,
                                 source='jmutube')
    res = render_to_response('jmutube-playlist.html',
                              { 'title': playlist.title,
                                'feed': 'http://%s%s' % (request.get_host(), reverse('jmutube-playlist-rss-feed', args=(user, playlist.id))) },
                              context_instance = RequestContext(request),
                              mimetype = 'application/binary')
    res["Content-Disposition"] = "attachment; filename=playlist.html"
    return res


def verify_user(func):
    def call_func(*args, **kwargs):
        if args[0].user.username != args[1]:
            raise Http404
        return func(*args, **kwargs)
    return call_func


@json_view
@verify_user
def playlist_json(request, user, title):
    playlist = get_object_or_404(Presentation, owner=request.user, name=title)
    return {
        'id': playlist.id,
         'user': playlist.owner.username,
        'title': playlist.title,
        'urltitle': playlist.name,
        'files': [{'id': item.record.id,
                    'title': item.record.title,
                    'delivery': item.type,
                    'deliveryoptions': 'B'} for item in playlist.items.all()]
        }


@json_view
@verify_user
def playlists_json(request, user):
    playlists = Presentation.objects.filter(owner__username=user, source='jmutube')
    return dict(playlists=[{'title': playlist.title, 'urltitle': playlist.name} for playlist in playlists])


@json_view
@verify_user
def store_playlist(request, user):
    id = int(request.POST['id'])
    title = request.POST['title']
    items = map(int, request.POST['items'].split(','))
    deliveries = request.POST['delivery'].split(',')
    # Filter to make sure all playlist items are owned by user
    records = Record.objects.filter(owner=request.user,
                                    source__startswith='jmutube-',
                                    id__in=items).values_list('id', flat=True)
    if id == 0:
        playlist = Presentation.objects.create(owner=request.user, title=title, source='jmutube')
    else:
        playlist = get_object_or_404(Presentation, owner=request.user, id=id, source='jmutube')
        playlist.title = title
        playlist.save()

    playlist.items.all().delete()
    count = 0
    for (item, delivery) in zip(items, deliveries):
        if item in records:
            count += 1
            PresentationItem.objects.create(presentation=playlist, record_id=item, order=count, type=delivery)
    return { 'message': 'Playlist saved', 'id': playlist.id, }


@json_view
@verify_user
def delete_playlist(request, user):
    id = int(request.POST['id'])
    playlist = get_object_or_404(Presentation, owner=request.user, id=id)
    playlist.delete();
    return { 'message': 'Playlist deleted' }


@json_view
@verify_user
def delete_tag(request, user):
    fileid = int(request.POST['id'])
    tag = int(request.POST['tag'])
    record = get_object_or_404(Record, owner__username=user, id=fileid)
    wrapper = OwnedWrapper.objects.get_for_object(user=record.owner, object=record)
    TaggedItem.objects.filter(object_id=wrapper.id, content_type=OwnedWrapper.t(OwnedWrapper), tag__id=tag).delete()
    return { 'message': 'Tag deleted' }
