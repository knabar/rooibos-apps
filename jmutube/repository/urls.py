from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template
from django.http import Http404

from views import *

# trigger 404 error to activate redirect middleware
def view404(request, *args, **kwargs):
    raise Http404

urlpatterns = patterns('',
    # Legacy URLs (no trailing slash)
    url(r'^([^/]+)/playlist/([^/]+)/rss$', view404, name='jmutube-playlist-rss-feed-legacy'), # may have "player=jmutube" as querystring
    url(r'^([^/]+)/file/([^/]+)/rss$', view404, name='jmutube-single-file-rss-feed-legacy'), # may have "player=jmutube" as querystring
    url(r'^([^/]+)/playlist/([^/]+)/play$', view404, name='jmutube-playlist-play-legacy'),
    # New URLs (trailing slash)
    url(r'^([^/]+)/playlist/([^/]+)/rss/$', playlist_rss_feed, name='jmutube-playlist-rss-feed'),
    url(r'^([^/]+)/file/(\d+)/([\w-]+)/rss/$', single_file_rss_feed, name='jmutube-single-file-rss-feed'),
    url(r'^([^/]+)/playlist/([^/]+)/play/$', playlist_play, name='jmutube-playlist-play'),
    # URLs that should not have been bookmarked or that don't have IDs in them
    url(r'^([^/]+)/playlist/([^/]+)/json/$', playlist_json, name='jmutube-playlist-json'),
    url(r'^([^/]+)/playlist/([^/]+)/download/$', playlist_download, name='jmutube-playlist-download'),
    url(r'^([^/]+)/playlists/json/$', playlists_json, name='jmutube-playlists-json'),
    url(r'^([^/]+)/store_playlist/$', store_playlist, name='jmutube-store-playlist'),
    url(r'^([^/]+)/delete_playlist/$', delete_playlist, name='jmutube-delete-playlist'),
    url(r'^([^/]+)/delete_tag/$', delete_tag, name='jmutube-delete-tag'),
)
