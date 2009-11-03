from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic.simple import direct_to_template

from views import *


urlpatterns = patterns('',
    url(r'^$', view_schedules, name='jmutube-crass-schedules'),
)
