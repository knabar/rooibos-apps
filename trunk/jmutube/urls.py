from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic.simple import direct_to_template
from rooibos.ui.views import upload_progress
from views import media_main, migrate_files, media_delete, media_rename, thumbnail, upload_file


urlpatterns = patterns('',
    (r'^$', direct_to_template, {'template': 'jmutube-home.html'}),

    url(r'^admin/(.*)', admin.site.root, {'SSL': True}, name='admin'),
    url(r'^mstatic/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DIR}, name='jmutube-master-static'),

    url(r'^accounts/login/$', login, {'template_name': 'registration/jmutube-login.html', 'SSL': True}, name='jmutube-login'),
    url(r'^accounts/logout/$', logout, {'template_name': 'registration/jmutube-logout.html'}, name='jmutube-logout'),
    url(r'^accounts/media/upload/$', upload_file, name='jmutube-upload'),
    url(r'^accounts/media/upload/progress/$', upload_progress, name='jmutube-upload-progress'),
    url(r'^accounts/media/(video|audio|images|crass|presentations)/$', media_main, name='jmutube-media'),
    url(r'^accounts/media/(video|audio|images|crass|presentations)/([^/]+)/$', media_main, name='jmutube-tagged-media'),
    url(r'^accounts/media/(video|audio|images|crass|presentations)/(\d+)/([\w-]+)/delete/$', media_delete, name='jmutube-media-delete'),
    url(r'^accounts/media/(video|audio|images|crass|presentations)/(\d+)/([\w-]+)/rename/$', media_rename, name='jmutube-media-rename'),
    url(r'^accounts/media/thumb/(?P<username>\w+)/(?P<id>\d+)/(?P<name>[-\w]+)/$', thumbnail, name='jmutube-thumbnail'),
    url(r'^accounts/media/$', media_main, {'type': 'video'}, name='jmutube-media-default'),
    url(r'^accounts/media/migrate/$', migrate_files, name='jmutube-migrate-files'),
    (r'^content/', include('apps.jmutube.repository.urls')),
    (r'^accounts/crass/', include('apps.jmutube.crass.urls')),
    url(r'^options/$', direct_to_template, {'template': 'jmutube-options.html'}, name='options'),
    url(r'^accounts/relay/$', direct_to_template, {'template': 'jmutube-relay.html'}, name="jmutube-relay"),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': 'django.conf'}, name='jmutube-jsi18n'),
    (r'^impersonate/', include('impersonate.urls')),
    url(r'^help/$', direct_to_template, {'template': 'jmutube-help.html'}, name='jmutube-help'),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.JMUTUBE_STATIC_FILES}, name='jmutube-static'),
    )
