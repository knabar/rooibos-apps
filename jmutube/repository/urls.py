from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template

from views import *

urlpatterns = patterns('',
    url(r'^([^/]+)/playlist/([^/]+)/rss', playlist_rss_feed, name='jmutube-playlist-rss-feed'),
    url(r'^([^/]+)/file/(\d+)/([\w-]+)/rss', single_file_rss_feed, name='jmutube-single-file-rss-feed'),
    url(r'^([^/]+)/playlist/([^/]+)/json', playlist_json, name='jmutube-playlist-json'),
    url(r'^([^/]+)/playlist/([^/]+)/play', playlist_play, name='jmutube-playlist-play'),
    url(r'^([^/]+)/playlist/([^/]+)/download', playlist_download, name='jmutube-playlist-download'),
    url(r'^([^/]+)/playlists/json', playlists_json, name='jmutube-playlists-json'),
    url(r'^([^/]+)/store_playlist', store_playlist, name='jmutube-store-playlist'),
    url(r'^([^/]+)/delete_playlist', delete_playlist, name='jmutube-delete-playlist'),
    url(r'^([^/]+)/delete_tag', delete_tag, name='jmutube-delete-tag'),
)
