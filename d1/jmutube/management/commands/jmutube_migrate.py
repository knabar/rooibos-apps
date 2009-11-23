from optparse import make_option
import os
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.contrib.auth.models import User, Group
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.conf import settings
from rooibos.contrib.impersonate.models import Impersonation
from rooibos.contrib.tagging.models import Tag
from rooibos.data.models import Record, Field, FieldValue, CollectionItem
from rooibos.storage.models import Media
from rooibos.presentation.models import Presentation, PresentationItem
from rooibos.util.models import OwnedWrapper
from apps.jmutube.crass.models import Computer, Mapping, Schedule
from apps.jmutube.util import get_jmutube_storage, get_jmutube_collection
from apps.jmutube.jmutubestorage import MIME_TYPES


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--file', '-f', dest='file', help='Legacy JMUtube data file created by dumpdata'),
    )
    help = "Migrates an old JMUtube installation's JSON database dump into the MDID3 based JMUtube"


    def handle(self, *args, **options):
        file = options.get('file')
        if not file:
            print "No input file specified"
            return
        if not os.path.isfile(file):
            print "File not found."
            return

        _data = simplejson.load(open(file))

        def data(model):
            return filter(lambda d: d['model'] == model, _data)

        # create user groups
        groups = dict()
        print "Creating groups"
        for d in data('auth.group'):
            group, created = Group.objects.get_or_create(name=d['fields']['name'])
            groups[d['pk']] = group
            print 'c' if created else '.',
        print

        # create users
        users = dict()
        print "Creating users"
        for d in data('auth.user'):
            g = d['fields'].pop('groups')
            u = d['fields'].pop('username')
            d['fields'].pop('user_permissions')
            user, created = User.objects.get_or_create(username=u,
                                                       defaults=d['fields'])
            users[d['pk']] = user

            for gid in g:
                user.groups.add(groups[gid])

            print 'c' if created else '.',
        print

        # create impersonations
        print "Creating Impersonations"
        for d in data('impersonate.impersonation'):
            g = d['fields'].pop('groups')
            u = d['fields'].pop('users')
            imp, created = Impersonation.objects.get_or_create(group=groups[d['fields']['group']])

            for uid in u:
                imp.users.add(users[uid])
            for gid in g:
                imp.groups.add(groups[gid])

            print 'c' if created else '.',
        print

        # create crass computers
        computers = dict()
        print "Creating CRASS computers"
        for d in data('crass.computer'):
            computer, created = Computer.objects.get_or_create(building=d['fields']['building'],
                                                               room=d['fields']['room'],
                                                               defaults=dict(mac_address=d['fields']['mac_address']))
            computers[d['pk']] = computer
            print 'c' if created else '.',
        print

        # create crass schedules
        print "Creating CRASS schedules"
        for d in data('crass.schedule'):
            schedule, created = Schedule.objects.get_or_create(start_time=d['fields']['start_time'],
                                                               end_time=d['fields']['end_time'],
                                                               computer=computers[d['fields']['computer']],
                                                               user=users[d['fields']['user']])
            print 'c' if created else '.',
        print

        # create crass mappings
        print "Creating CRASS mappings"
        for d in data('crass.mapping'):
            mapping, created = Mapping.objects.get_or_create(time_stamp=d['fields']['time_stamp'],
                                                               source_file=d['fields']['source_file'],
                                                               target_file=d['fields']['target_file'],
                                                               user=users[d['fields']['user']])
            print 'c' if created else '.',
        print

        # create records and media
        print "Creating records and media"
        storage = get_jmutube_storage()
        collection=get_jmutube_collection()
        title_field = Field.objects.get(name='title', standard__prefix='dc')
        records = dict()
        files = dict()
        allmedia = dict()
        for m in Media.objects.filter(storage=storage):
            allmedia[m.url] = m.record
        for d in data('repository.file'):
            files[d['pk']] = d['fields']['file']
            mimetype = MIME_TYPES.get(os.path.splitext(d['fields']['file'])[1], 'application/octet-stream')
            url = '%s/%s/%s' % (users[d['fields']['user']].username,
                                                   d['fields']['type'],
                                                   d['fields']['file'])
            record = allmedia.get(url)
            if record:
                records[d['pk']] = record
                print '.',
                continue
            record = Record.objects.create(owner=users[d['fields']['user']],
                                           name=d['fields']['title'],
                                           source='jmutube-%s' % d['fields']['type'])
            records[d['pk']] = record
            media = Media.objects.create(record=record,
                                 url=url,
                                 storage=storage,
                                 mimetype=mimetype)
            CollectionItem.objects.create(collection=collection, record=record)
            FieldValue.objects.create(record=record,
                                       field=title_field,
                                       value=d['fields']['title'],
                                       order=1)
            Tag.objects.add_tag(OwnedWrapper.objects.get_for_object(user=users[d['fields']['user']],
                                                                    object=record), 'JMUtube')
            print 'c',
        print

        # create presentations
        print "Creating presentations"
        presentations = dict()
        for d in data('repository.playlist'):
            presentation, created = Presentation.objects.get_or_create(source='jmutube',
                                                               owner=users[d['fields']['user']],
                                                               title=d['fields']['title'])
            presentations[d['pk']] = presentation
            print 'c' if created else '.',
        print

        # create presentation redirects
        print "Creating presentation redirects"
        site = Site.objects.get(id=settings.SITE_ID)
        for oldid, presentation in presentations.iteritems():
            redirect, created1 = Redirect.objects.get_or_create(site=site,
                old_path=reverse('jmutube-playlist-rss-feed-legacy', args=(presentation.owner.username, oldid)),
                new_path=reverse('jmutube-playlist-rss-feed', args=(presentation.owner.username, presentation.id))
                )
            redirect, created2 = Redirect.objects.get_or_create(site=site,
                old_path=reverse('jmutube-playlist-rss-feed-legacy', args=(presentation.owner.username, oldid)) + '?player=jmutube',
                new_path=reverse('jmutube-playlist-rss-feed', args=(presentation.owner.username, presentation.id)) + '?player=jmutube'
                )
            redirect, created3 = Redirect.objects.get_or_create(site=site,
                old_path=reverse('jmutube-playlist-play-legacy', args=(presentation.owner.username, oldid)),
                new_path=reverse('jmutube-playlist-play', args=(presentation.owner.username, presentation.id))
                )
            print 'c' if created1 or created2 or created3 else '.',
        print

        print "Creating file redirects"
        for oldid, record in records.iteritems():
            try:
                redirect, created1 = Redirect.objects.get_or_create(site=site,
                    old_path=reverse('jmutube-single-file-rss-feed-legacy', args=(presentation.owner.username, files[oldid])),
                    new_path=reverse('jmutube-single-file-rss-feed', args=(presentation.owner.username, record.id, record.name))
                    )
                redirect, created2 = Redirect.objects.get_or_create(site=site,
                    old_path=reverse('jmutube-single-file-rss-feed-legacy', args=(presentation.owner.username, files[oldid])) + '?player=jmutube',
                    new_path=reverse('jmutube-single-file-rss-feed', args=(presentation.owner.username, record.id, record.name)) + '?player=jmutube'
                    )
                print 'c' if created1 or created2 else '.',
            except Exception, ex:
                print 'X',
        print

        # create presentation items
        print "Creating presentation items"
        for d in data('repository.playlistitem'):
            item, created = PresentationItem.objects.get_or_create(
                type=d['fields']['delivery'],
                order=d['pk'],
                presentation=presentations[d['fields']['playlist']],
                record=records[d['fields']['file']]
            )
            print 'c' if created else '.',
        print

        # create tags
        print "Creating tags"
        tags = dict()
        for d in data('tagging.tag'):
            tags[d['pk']] = d['fields']['name']
        for d in data('tagging.taggeditem'):
            record = records.get(d['fields']['object_id'])
            if record:
                Tag.objects.add_tag(OwnedWrapper.objects.get_for_object(user=record.owner, object=record),
                                    '"%s"' % tags[d['fields']['tag']])
                print '-',
            else:
                print 'X',
        print
