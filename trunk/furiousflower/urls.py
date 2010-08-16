from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.views.generic.simple import direct_to_template
from views import *


urlpatterns = patterns('',
     url(r'^$', main, name='furiousflower-main'),
     url(r'^css/$', direct_to_template, {'template': 'furiousflower.css', 'mimetype': 'text/css'}, name='furiousflower-css'),
     url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.FURIOUSFLOWER_STATIC_FILES}, name='furiousflower-static'),
     url(r'^view/(?P<id>[\d]+)/(?P<name>[-\w]+)/$', view, name='furiousflower-view'),
    )
