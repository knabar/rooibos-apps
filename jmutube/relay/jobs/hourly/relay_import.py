from xml.dom.minidom import parse
from django_extensions.management.jobs import HourlyJob
from django.conf import settings
from django.contrib.auth.models import User
import os
import zipfile
import shutil
import re
from apps.jmutube.util import make_unique, get_jmutube_storage
from tagging.models import Tag
from rooibos.util.models import OwnedWrapper
import rooibos.contrib.djangologging.middleware # does not get loaded otherwise
import logging
import time

class Job(HourlyJob):
    help = "Import relay files"

    def execute(self):

        def getElement(dom, *tagname):
            result = dom
            for t in tagname:
                result = result.getElementsByTagName(t)[0]
            return result

        def move_or_remove(file, sourcedir, targetdir):
            if os.path.exists(os.path.join(targetdir, file)):
                logging.debug("Relay: File %s exists in %s" % (file, targetdir))
                os.remove(os.path.join(sourcedir, file))
            else:
                shutil.move(os.path.join(sourcedir, file), targetdir)

        logging.info("Relay import starting")
        
        storage = get_jmutube_storage()
        files = filter(lambda f: f.endswith('.xml'), os.listdir(settings.JMUTUBE_RELAY_INCOMING_FOLDER))
        regex = re.compile('[^0-9a-z]+', flags=re.IGNORECASE)
        for file in files:
            age = time.time() - os.path.getmtime(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, file))
            if age < 600:
                logging.debug('Relay skipping file %s with age %s' % (file, age))
                continue
            try:
                dom = parse(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, file))
                title = getElement(dom, 'presentation', 'title').firstChild.data
                presenter = getElement(dom, 'presentation', 'presenter', 'userName').firstChild.data
                user = User.objects.get(username=presenter)
                files = [f.getAttribute('name') for f in
                         getElement(dom, 'presentation', 'outputFiles', 'fileList').getElementsByTagName('file')]
                
                if len(files) > 1:
                    logging.info("Relay importing presentation %s" % file)
                    # Handle presentation
                
                    outfile = regex.sub('_', os.path.splitext(file)[0])
                    outfile = make_unique(os.path.join(presenter, 'presentations', outfile + '.zip'))
                    outfilename = os.path.basename(outfile)
                    # create zipped version
                    camrec = False
                    zipfilename = os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, outfilename)
                    zip = zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED)
                    for f in files:
                        zip.write(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, f), f.encode('ascii'))
                        camrec = camrec or f.endswith('.camrec')
                    zip.write(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, file), file)
                    zip.close()
                    # create folder and move everything over
                    outdir = storage.storage_system.path(outfile + '.content')
                    if not os.path.exists(outdir):
                        os.mkdir(outdir)
                    for f in files:
                        move_or_remove(f, settings.JMUTUBE_RELAY_INCOMING_FOLDER, outdir)
                    move_or_remove(file, settings.JMUTUBE_RELAY_INCOMING_FOLDER, outdir)
                    try:
                        shutil.move(zipfilename, storage.storage_system.path(outfile))
                    except:
                        logging.error("Cannot move ZIP file %s" % zipfilename)
                        os.remove(zipfilename)
    
                    # create entry point
                    html = filter(lambda f: f.endswith(".htm") or f.endswith(".html"), os.listdir(outdir))
                    if len(html) == 1 and not html in ('default.htm', 'default.html', 'index.htm', 'index.html'):
                        shutil.copy(os.path.join(outdir, html[0]), os.path.join(outdir, 'index.html'))

                    # add file entry
                    logging.info('Relay creating record for %s: %s (presentations)' % (user, outfile))
                    record = storage.storage_system.create_record_for_file(user, outfile, 'presentations')

                else:
                    logging.info("Relay importing single file %s" % file)
                    # Handle single file upload

                    name, ext = os.path.splitext(files[0])
                    outfile = regex.sub('_', name) + ext
                    outfile = make_unique(os.path.join(presenter, 'video', outfile))
                    outfilename = os.path.basename(outfile)
                    
                    camrec = outfile.endswith('.camrec')

                    try:
                        logging.info('Relay creating record for %s: %s (video)' % (user, outfile))
                        record = storage.storage_system.create_record_for_file(user, outfile, 'video')
                    except Exception, e:
                        logging.error("Cannot create record - unsupported file type? [%s]" % e)
                        continue

                    try:
                        shutil.move(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, files[0]),
                                    storage.storage_system.path(outfile))
                    except Exception, e:
                        logging.error("Cannot move file %s to %s [%s]" % (files[0], outfile, e))
                        record.delete()
                        continue
                    
                    try:
                        os.remove(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, file))
                    except Exception, e:
                        logging.error("Cannot remove file %s [%s]" % (file, e))
                        continue

                # add tags
                wrapper = OwnedWrapper.objects.get_for_object(user=user, object=record)
                Tag.objects.add_tag(wrapper, 'Relay')
                if camrec:
                    Tag.objects.add_tag(wrapper, 'CamRec')
            except Exception, e:
                logging.error(e)
