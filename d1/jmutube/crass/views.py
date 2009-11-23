from django.shortcuts import render_to_response
from django.template import RequestContext
from django import forms
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
import os
from models import Computer, Schedule, Mapping
from datetime import date, datetime, timedelta

from apps.jmutube.util import jmutube_login_required

"""
def time_choices():
    c = []
    for h in range(0, 24):
        h2 = h % 12
        if h2 == 0: h2 = 12
        for m in range(0, 60, 10):
            c += (('%02d:%02d:00' % (h, m), '%02d:%02d %s' % (h2, m, h < 12 and 'am' or 'pm')),)
    return c

def default_time(houroffset=0):
    d = datetime.now() + timedelta(0, 0, 0, 0, 0, houroffset)
    m = ((d.minute / 10 + 1) * 10) % 60
    h = m == 0 and (d.hour + 1) or d.hour
    if (h > 23): h = 0
    return '%02d:%02d:00' % (h, m)
"""
def time_choices():
    c = []
    for h in range(0, 24):
        h2 = h % 12
        if h2 == 0: h2 = 12
        for m in range(0, 6):
            c += ((h * 6 + m, '%02d:%02d %s' % (h2, m * 10, h < 12 and 'am' or 'pm')),)
    c += ((24 * 6, '12:00 am'),)
    return c

def default_time(houroffset=0):
    d = datetime.now() + timedelta(0, 0, 0, 0, 0, houroffset)
    m = ((d.minute / 10 + 1) * 10) % 60
    h = m == 0 and (d.hour + 1) or d.hour
    if (h > 23):
        h = 24
        m = 00
    return h * 6 + m / 10


def default_date():
    t = date.today()
    return t.strftime("%m/%d/%y")

class ScheduleForm(forms.ModelForm):

    date = forms.DateField(widget=forms.TextInput(attrs = {'class': 'vDateField'}))
    start = forms.ChoiceField(choices=time_choices())
    end = forms.ChoiceField(choices=time_choices())

    class Meta:
        model = Schedule
        exclude = ('user', 'start_time', 'end_time')


@jmutube_login_required
def view_schedules(request):

    if request.method == 'POST':

        delete_schedule = filter(lambda k: k.startswith('delete_schedule_'), request.POST.keys())
        if delete_schedule:
            id = int(delete_schedule[0][16:])
            Schedule.objects.filter(user__username=request.user.username, id=id).delete()
            return HttpResponseRedirect(reverse('jmutube-crass-schedules'))
        else:
            form = ScheduleForm(request.POST)
            if form.is_valid():
                schedule = form.save(commit=False)
                schedule.user = request.user
                date = form.cleaned_data['date'];
                start = int(form.cleaned_data['start'])
                end = int(form.cleaned_data['end'])
                schedule.start_time = datetime(date.year, date.month, date.day, start / 6, (start % 6) * 10)
                if (end < start):
                    date = date + timedelta(1)
                schedule.end_time = datetime(date.year, date.month, date.day, end / 6, (end % 6) * 10)
                schedule.save()
                return HttpResponseRedirect(reverse('jmutube-crass-schedules'))

    else:
        form = ScheduleForm(initial={'start': default_time(), 'end': default_time(1), 'date': default_date()})

    d = datetime.now()-timedelta(7)
    schedules = Schedule.objects.filter(user__username=request.user.username, start_time__gte=d)
    mappings = [dict(time_stamp=m.time_stamp, file=os.path.basename(m.target_file))
                for m in Mapping.objects.filter(user__username=request.user.username, time_stamp__gte=d)]

    return render_to_response("jmutube-schedules.html",
                              {'schedules': schedules,
                               'form': form,
                               'mappings': mappings,
                               },
                              context_instance = RequestContext(request))
