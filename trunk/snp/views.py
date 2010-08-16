from __future__ import with_statement
from django import forms
from django.conf import settings
from django.conf.urls.defaults import url
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db.models.aggregates import Count, Min
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
from rooibos.solr.views import run_search
from rooibos.viewers.viewers.audiotextsync import AudioTextSync


def main(request):
    return render_to_response('snp-main.html',
                              {  },
                              context_instance=RequestContext(request))


def browse(request):
    
    collection = Collection.objects.get(name='shenandoah-national-park')
    
    interview_numbers = dict(FieldValue.objects.filter(record__collection=collection,
                                                  field__label='Identifier').values_list('record__id', 'value'))
    
    def get_values(label):
        v = FieldValue.objects.filter(
            Q(label=label) | Q(field__label=label),
            record__collection=collection
            ).annotate(min_record_id=Min('record__id')).values('value', 'min_record_id').annotate(num_records=Count('record__id')).order_by('value')
        for i in v:
            i['interview_number'] = interview_numbers.get(i['min_record_id'])
        return v
        
    interviewees = get_values('Interviewee')        
    family_names = get_values('Family Names')
    personal_names = get_values('Personal Names')
    place_names = get_values('Place Names')
    subjects = get_values('Subject')
        
    return render_to_response('snp-browse.html',
                          { 'interviewees': interviewees,
                            'family_names': family_names,
                            'personal_names': personal_names,
                            'place_names': place_names,
                            'subjects': subjects,
                            },
                          context_instance=RequestContext(request))


def search(request):
    
    collection = Collection.objects.get(name='shenandoah-national-park')
    q = request.GET.get('q', '')
    try:
        p = int(request.GET.get('p', 1))
    except ValueError:
        p = 1
    
    f = request.GET.get('f')
    v = request.GET.get('v')
    
    if f and v:
        
        records = [fv.record for fv in FieldValue.objects.select_related('record').filter(record__collection=collection,
                                  label=f,
                                  value=v)]
        
        prev_page = next_page = None

    else:
        
        (hits, records, search_facets, orfacet, query, fields) = run_search(
            request.user,
            keywords=q,
            criteria=['allcollections:%d' % collection.id],
            sort='subject_sort asc',
            page=p,
            pagesize=20,
            produce_facets=False)
        
        prev_page = max(1, p - 1)
        next_page = min(p + 1, (hits - 1) / 20 + 1) if hits > 0 else 1
    
    results = []
    
    for record in records:
        
        mapping = {'Interviewee': 'interviewee',
                   'Identifier': 'interview_number',
                   'Location/Date': 'location_date',
                   'Description': 'description',
                   'Interviewer/Transcriber': 'interviewer_transcriber'}
        
        result = dict()
        
        for fv in record.get_fieldvalues():
            if mapping.has_key(fv.resolved_label):
                result[mapping[fv.resolved_label]] = fv.value
        
        results.append(result)
        
     
    return render_to_response('snp-search.html',
                              { 'results': results,
                                'query': q,
                                'prev_page': prev_page,
                                'next_page': next_page,
                               },
                              context_instance=RequestContext(request))


def interview(request, number):

    collection = Collection.objects.get(name='shenandoah-national-park')
    record = get_object_or_404(FieldValue,
                               record__collection=collection,
                               field__label='Identifier',
                               value=number).record

    description = FieldValue.objects.filter(record=record,
                                            field__label='Description',
                                            ).values_list('value', flat=True)
    

    return render_to_response('snp-interview.html',
                              {'record': record,
                               'description': description[0] if description else None,
                               'interview_number': number,
                               'has_audio_transcript': AudioTextSync().analyze(record, request.user) == FULL_SUPPORT,
                               },
                              context_instance=RequestContext(request))

    

def transcript(request, number):
    
    
    collection = Collection.objects.get(name='shenandoah-national-park')
    record = get_object_or_404(FieldValue,
                               record__collection=collection,
                               field__label='Identifier',
                               value=number).record
    return AudioTextSync().view(request, record.id, record.name, template='snp.html')
    