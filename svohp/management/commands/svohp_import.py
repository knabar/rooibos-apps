from django.core.management.base import BaseCommand
from django.conf import settings
from rooibos.util.BeautifulSoup import BeautifulSoup, NavigableString
from rooibos.data.models import Record, Field, CollectionItem, FieldValue
from rooibos.storage.models import Media
from apps.svohp.util import get_svohp_collection, get_svohp_storage
from apps.svohp import pyPdf
import os, re


def getPDFContent(path):
    content = ""
    pdf = pyPdf.PdfFileReader(file(path, "rb"))
    for i in range(0, pdf.getNumPages()):
        content += pdf.getPage(i).extractText() + "\n"
    return content


class Command(BaseCommand):
    help = """
    Performs the initial data import.

    WARNING: THIS REMOVES ALL EXISTING RECORDS IN THE SVOHP COLLECTION!

    Call with 'import' to confirm."""
    args = 'confirm'

    def clean_string(self, s):
        return s.replace('\n', ' ').strip()

    def get_items(self, file, heading_only=False):
        html = open(os.path.join(settings.SVOHP_MEDIA_ROOT, file), 'r').read()
        html = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
        content = html.find(id='content')
        result = dict()
        for item in content.findChildren('strong'):
            heading = self.clean_string(''.join(filter(lambda s: type(s)==NavigableString, item.contents)))
            if not heading:
                print "Bad heading (%s):" % file, item.contents
            if heading:
                h = re.search(r'^(.+), interview(ed)? by (.+) on (.+)$', heading)
                if not h:
                    print "Bad heading (%s):" % file, heading
                    continue
                if heading_only:
                    result[heading] = None
                    continue
                tag = item.parent.findNextSibling('p')
                description = tag.string
                attachments = []
                while True:
                    tag = tag.findNextSibling('p')
                    if not tag.get('align') == 'right':
                        break
                    for a in tag.findAll('a'):
                        attachments.append(dict(url=a.get('href'),
                                                ext=a.get('href')[-3:].lower(),
                                                title=self.clean_string(a.string)))
                d = re.search(r'^(.+) Duration:? ((\d+) hr )?(\d+) ?min( (\d+) sec)?\.', description, re.MULTILINE)
                if not d:
                    duration = 0
                else:
                    description = d.group(1)
                    duration = int(d.group(3) or '0') * 3600 + int(d.group(4)) * 60 + int(d.group(6) or '0')
                result[heading] = dict(interviewee=h.group(1),
                                          interviewer=h.group(3),
                                          date=h.group(4),
                                          description=description,
                                          duration=duration,
                                          attachments=attachments)
        return result


    def get_topics(self):
        html = open(os.path.join(settings.SVOHP_MEDIA_ROOT, 'browse.html'), 'r').read()
        html = BeautifulSoup(html, convertEntities=BeautifulSoup.HTML_ENTITIES)
        content = html.find(id='content')
        topics = dict()
        for a in content.findAll('a'):
            topics[self.clean_string(a.string)] = a.get('href').replace('%20', ' ')
        return topics


    def handle(self, *confirm, **options):

        if confirm != ('import',):
            print self.help
            return

        items = self.get_items('interviews.html')
        topics = self.get_topics()

        for topic, file in topics.iteritems():
            for i in self.get_items(file, heading_only=True).iterkeys():
                if not items.has_key(i):
                    print "Unknown person (%s):" % file, i
                else:
                    items[i].setdefault('topics', []).append(topic)

        coll = get_svohp_collection()
        storage = get_svohp_storage()

        Record.objects.filter(source='svohp').delete()

        fields = dict((f.name, f) for f in Field.objects.filter(standard__prefix='dc'))

        for item in items.itervalues():

            r = Record.objects.create(name=item['interviewee'], source='svohp')
            CollectionItem.objects.create(record=r, collection=coll)

            FieldValue.objects.create(record=r,
                                       field=fields['title'],
                                       order=1,
                                       value=item['interviewee'],
                                       label='Interviewee')
            FieldValue.objects.create(record=r,
                                       field=fields['contributor'],
                                       order=2,
                                       value=item['interviewer'],
                                       label='Interviewer')
            FieldValue.objects.create(record=r,
                                       field=fields['date'],
                                       order=3,
                                       value=item['date'])
            FieldValue.objects.create(record=r,
                                       field=fields['description'],
                                       order=4,
                                       value=item['description'])
            FieldValue.objects.create(record=r,
                                       field=fields['coverage'],
                                       refinement='temporal',
                                       order=5,
                                       numeric_value=item['duration'],
                                       value='%02d:%02d:%02d' % (item['duration'] / 3600, item['duration'] % 3600 / 60, item['duration'] % 60),
                                       label='Duration')
            for topic, order in zip(item['topics'], range(6, 100)):
                FieldValue.objects.create(record=r,
                                           field=fields['subject'],
                                           order=order,
                                           value=topic)

            mimetypes = dict(mp3='audio/mpeg',
                             wav='audio/x-wav',
                             pdf='application/pdf',
                             doc='application/msword',
                             jpg='image/jpeg')

            transcript = False
            for att in item['attachments']:

                if att['title'].lower().find('transcript') > -1:
                    transcript = True
                elif len(att['title']) > 6:
                    transcript = False

                if att['ext'] in ('wav', 'mp3') or (att['ext'] in ('doc', 'pdf') and transcript):
                    m = Media.objects.create(record=r,
                                         storage=storage,
                                         url=att['url'].replace('%20', ' '),
                                         name=item['interviewee'] + '-' + att['ext'],
                                         mimetype=mimetypes[att['ext']])
                    if transcript and att['ext'] == 'pdf':
                        content = getPDFContent(storage.storage_system.path(m.url))
                        FieldValue.objects.create(record=r,
                                                  field=fields['description'],
                                                  label='Transcript',
                                                  hidden=True,
                                                  value=content)
