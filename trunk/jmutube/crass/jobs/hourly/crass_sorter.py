from django_extensions.management.jobs import HourlyJob
from django.conf import settings
import os
import shutil
import re
import time
import logging
from datetime import datetime
from tagging.models import Tag
from rooibos.util.models import OwnedWrapper
from apps.jmutube.crass.models import Mapping, Schedule
from apps.jmutube.util import get_jmutube_storage

class Job(HourlyJob):
    help = "Sort CRASS video files"
    file_re = re.compile(r'^(?P<mac>[0-9a-f]{12})_(?P<y>\d{4})-(?P<m>\d\d)-(?P<d>\d\d)_(?P<h>\d\d)-(?P<n>\d\d)-(?P<s>\d\d)\.mp4$', flags=re.IGNORECASE)

    def execute(self):
        storage = get_jmutube_storage()
        logging.info('CRASS sorter starting')
        for file in os.listdir(settings.JMUTUBE_CRASS_MISC_FOLDER):
        
            age = time.time() - os.path.getmtime(os.path.join(settings.JMUTUBE_CRASS_MISC_FOLDER, file))
            if age < 600:
                logging.debug('CRASS skipping file %s with age %s' % (file, age))
                continue
                
            logging.debug('Processing %s' % file)
            match = Job.file_re.match(file)
            if match:
                dt = datetime(int(match.group('y')), int(match.group('m')), int(match.group('d')),
                              int(match.group('h')), int(match.group('n')), int(match.group('s')))
                schedules = Schedule.objects.filter(computer__mac_address__iexact=match.group('mac'),
                                                    start_time__lte=dt, end_time__gte=dt)
                if not schedules:
                    logging.debug("no schedule found")
                    continue
                schedule = schedules[0]
                title = '%s %s (%s)' % (schedule.computer.building, schedule.computer.room, dt)
                newname = os.path.join(schedule.user.username,
                                         'video',
                                        (schedule.computer.building + ' ' + schedule.computer.room + ' '
                                         + file[13:-4]).replace(' ', '_') + '.mp4')
                if not storage.file_exists(newname):
                    # add mapping log entry
                    Mapping.objects.create(source_file=file, target_file=newname, user=schedule.user)
                    # move file
                    shutil.move(os.path.join(settings.JMUTUBE_CRASS_MISC_FOLDER, file), storage.storage_system.path(newname))
                    # add file entry
                    record = storage.storage_system.create_record_for_file(schedule.user, newname, 'video')
                    # add tags
                    wrapper = OwnedWrapper.objects.get_for_object(user=schedule.user, object=record)
                    Tag.objects.add_tag(wrapper, '"%s %s"' % (schedule.computer.building, schedule.computer.room))
                    Tag.objects.add_tag(wrapper, 'CRASS')
                    Tag.objects.add_tag(wrapper, '"Week %s"' % dt.isocalendar()[1])
                    Tag.objects.add_tag(wrapper, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dt.weekday()])
                    logging.debug("-> %s" % newname)
                else:
                    logging.debug("target file already exists")
            else:
                logging.debug("invalid file")
