from django.http import HttpResponse, Http404,  HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response
from django.template import RequestContext
from rooibos.util import json_view
from rooibos.access import check_access
from rooibos.data.models import Field, FieldValue
from util import get_svohp_collection
import re


def list(request):

    collection = get_svohp_collection()

    return render_to_response('svohp-interviews.html',
                              {'records': ([dict((fv.field.name, fv.value) for fv in r.get_fieldvalues()), r]
                                           for r in collection.records.all()),
                               },
                              context_instance=RequestContext(request))


def interview(request, name):

    collection = get_svohp_collection()
    record = get_object_or_404(collection.records, name=name)
    fvs = record.get_fieldvalues(hidden=True)
    transcript = re.sub('(\n\s*)+', '\n\n', filter(lambda f: f.label=='Transcript', fvs)[0].value).strip()
    markers = filter(lambda f: f.label=='Markers', fvs)
    if markers:
        markers = dict(map(lambda v: v.split(','), markers[0].value.split('\n')))
    mp3 = record.media_set.filter(mimetype='audio/mpeg')[0]
    edit = check_access(request.user, collection, write=True) and (request.GET.get('edit') == 'edit')

    return render_to_response('svohp-interview.html',
                              {'data': dict((fv.field.name, fv.value) for fv in filter(lambda f: not f.hidden, fvs)),
                               'transcript': transcript,
                               'record': record,
                               'mp3url': mp3.get_absolute_url(),
                               'edit': edit,
                               'markers': markers,
                               },
                              context_instance=RequestContext(request))


@json_view
def savemarkers(request):
    if request.method == "POST":
        collection = get_svohp_collection()
        check_access(request.user, collection, write=True, fail_if_denied=True)
        record = get_object_or_404(collection.records, name=request.POST['name'])
        field = Field.objects.get(standard__prefix='dc', name='description')
        fv, created = FieldValue.objects.get_or_create(record=record,
                                              field=field,
                                              hidden=True,
                                              label='Markers',
                                              defaults=dict(value=''))
        if created or fv.value == '':
            markers = dict()
        else:
            markers = dict(map(lambda v: v.split(','), fv.value.split('\n')))
        markers[request.POST['index']] = request.POST['time']
        to_remove = []
        prev_val = None
        for key in sorted(markers.keys()):
            if prev_val:
                if prev_val >= markers[key]:
                    to_remove.append(key)
            else:
                prev_val = markers[key]
        for key in to_remove:
            del markers[key]
        fv.value = '\n'.join('%s,%s' % (v,k) for v,k in markers.iteritems())
        fv.save()
        return dict(message="Markers saved")
    else:
        return dict(result='Invalid method. Use POST.')
