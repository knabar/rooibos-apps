from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic.simple import direct_to_template
from views import list, interview, savemarkers

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template': 'svohp-home.html'}, name='svohp-main'),

    url(r'^interviews.html$', list),
    url(r'^interview/(?P<name>[\w-]+)/$', interview, name='svohp-interview'),
    url(r'^savemarkers/$', savemarkers, name='svohp-savemarkers'),
    url(r'^index.htm$', direct_to_template, {'template': 'svohp-home.html'}),
    url(r'^contact.html$', direct_to_template, {'template': 'svohp-contact.html'}),
    url(r'^links.html$', direct_to_template, {'template': 'svohp-links.html'}),

    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.SVOHP_STATIC_FILES}, name='svohp-static'),
    )
