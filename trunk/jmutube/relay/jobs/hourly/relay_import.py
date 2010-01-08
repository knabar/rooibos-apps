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
                print "File %s exists in %s" % (file, targetdir)
                os.remove(os.path.join(sourcedir, file))
            else:
                shutil.move(os.path.join(sourcedir, file), targetdir)

        storage = get_jmutube_storage()
        files = filter(lambda f: f.endswith('.xml'), os.listdir(settings.JMUTUBE_RELAY_INCOMING_FOLDER))
        regex = re.compile('[^0-9a-z]+', flags=re.IGNORECASE)
        for file in files:
            try:
                dom = parse(os.path.join(settings.JMUTUBE_RELAY_INCOMING_FOLDER, file))
                title = getElement(dom, 'presentation', 'title').firstChild.data
                presenter = getElement(dom, 'presentation', 'presenter', 'userName').firstChild.data
                user = User.objects.get(username=presenter)
                files = [f.getAttribute('name') for f in
                         getElement(dom, 'presentation', 'outputFiles', 'fileList').getElementsByTagName('file')]
                print file
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
                    print "Cannot move ZIP file %s" % zipfilename
                    os.remove(zipfilename)

                # create entry point
                html = filter(lambda f: f.endswith(".htm") or f.endswith(".html"), os.listdir(outdir))
                if len(html) == 1 and not html in ('default.htm', 'default.html', 'index.htm', 'index.html'):
                    shutil.copy(os.path.join(outdir, html[0]), os.path.join(outdir, 'index.html'))

                # add file entry
                record = storage.storage_system.create_record_for_file(user, outfile, 'presentations')
                # add tags
                wrapper = OwnedWrapper.objects.get_for_object(user=user, object=record)
                Tag.objects.add_tag(wrapper, 'Relay')
                if camrec:
                    Tag.objects.add_tag(wrapper, 'CamRec')
                print "done"
            except Exception, e:
                print e
