from __future__ import with_statement
from django import forms
from django.conf import settings
from django.conf.urls.defaults import url
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.forms.util import ErrorList
from django.http import HttpResponse, Http404,  HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.safestring import mark_safe
from rooibos.access import accessible_ids, accessible_ids_list, check_access, filter_by_access
from rooibos.data.models import Record, Collection, FieldValue, standardfield, get_system_field
from rooibos.storage.models import Storage
from rooibos.util import json_view
from rooibos.viewers import NO_SUPPORT, PARTIAL_SUPPORT, FULL_SUPPORT


def main(request):
    collection = Collection.objects.get(name='furious-flower')
    relation_field = standardfield('relation')
    order = FieldValue.objects.filter(field=relation_field, record__collection=collection).values_list('record__id', 'value')
    order = sorted(order, key=lambda (r,o): int(o))
    records = dict((r.id, r) for r in collection.records.all())
    sorted_records = []
    for r, o in order:
        if records.has_key(r):
            sorted_records.append(records.pop(r))
    sorted_records.extend(records.values())
    
    return render_to_response('furiousflower-main.html',
                              {'records': sorted_records, },
                              context_instance=RequestContext(request))



def view(request, id, name):
    
    collection = Collection.objects.get(name='furious-flower')

    record = get_object_or_404(Record.objects.filter(collection=collection, id=id).distinct())

    storage = Storage.objects.get(name='furious-flower')
    
    media = record.media_set.filter(master=None,
                                 storage=storage,
                                 mimetype__in=('video/mp4', 'video/quicktime'))
    if not media:
        raise Http404()
        
    return render_to_response('furiousflower-view.html',
                              {'record': record,
                               'media': media[0],
                               },
                              context_instance=RequestContext(request))
