from django.conf import settings
from rooibos.data.models import CollectionItem, FieldValue, Field, Record
from rooibos.storage.models import Media
from rooibos.util.models import OwnedWrapper
from rooibos.storage.localfs import LocalFileSystemStorageSystem
from util import get_jmutube_storage, get_jmutube_collection, all_files, us_to_sp
from tagging.models import Tag
import os, errno, shutil
from unzip import unzip
from StringIO import StringIO
import logging


FILE_TYPES = {
    'video': ('*.mp4', '*.flv', '*.mov', '*.camrec'),
    'audio': ('*.mp3', '*.m4a'),
    'presentations': ('*.zip',),
    'crass': (),
}


MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.m4v': 'video/x-m4v',
    '.mov': 'video/quicktime',
    '.flv': 'video/x-flv',
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4a-latm',
    '.zip': 'application/zip',
    '.camrec': 'application/octet-stream',
}


def determine_type(filename):
    ext = '*' + os.path.splitext(filename)[1].lower()
    for type in FILE_TYPES:
        if ext in FILE_TYPES[type]:
            return type
    return None


class JMUtubeStorageSystem(LocalFileSystemStorageSystem):

    def list_files(self, subdir=None, patterns=[]):
        path = self.path(subdir)
        patterns = '*' if not patterns else ';'.join(patterns)
        return map(lambda f: f[len(self.location) + 1:],
                filter(lambda f: os.path.split(f)[1][0] != ".",
                      all_files(path, patterns=patterns, single_level=True)))

    def get_absolute_media_url(self, storage, media, delivery=None):
        if not delivery:
            delivery='P'
        m = media.mimetype
        if delivery == 'P' or (m[:5] != 'video' and m[:5] != 'audio'):
            return "http://jmutube.cit.jmu.edu/users/%s" % media.url.replace('\\', '/')
        else:
            prot = 'mp4:' if m in ('video/mp4','video/quicktime', 'audio/mp4a-latm') else ''
            prot = 'mp3:' if m in ('audio/mpeg') else prot
            file = media.url[:-4] if m in ('audio/mpeg') else media.url
            return "rtmp://flash.streaming.jmu.edu:80/videos/users/%s%s" % (
                    prot, file.replace('\\', '/'))

    def get_jmutube_player_url(self, storage, media, delivery=None):
        return self.get_absolute_media_url(storage, media, delivery='S' if media.mimetype == 'audio/mpeg' else delivery)

    def save(self, name, content):
        super(JMUtubeStorageSystem, self).save(name, content)
        if os.path.splitext(name)[1].lower() == '.zip':
            self._unzip_archive(name)

    def delete(self, name):
        super(JMUtubeStorageSystem, self).delete(name)
        if self.exists(name + '.content'):
            shutil.rmtree(self.path(name + '.content'), ignore_errors=True)

    def _unzip_archive(self, name):
        file = self.path(name)
        dirname = file + ".content"
        unzip(verbose=False).extract(file, dirname)
        # check for single root directory
        dirs = os.listdir(dirname)
        if len(dirs) == 1 and os.path.isdir(os.path.join(dirname, dirs[0])):
            dir = os.path.join(dirname, dirs[0])
            os.rename(dir, dir + ".jmutube.temp")
            dir += ".jmutube.temp"
            for f in os.listdir(dir):
                shutil.move(os.path.join(dir, f), os.path.join(dirname, f))
            os.rmdir(dir)
        # check for entry point
        html = filter(lambda f: f.endswith(".htm") or f.endswith(".html"), os.listdir(dirname))
        if len(html) == 1 and not html in ('default.htm', 'default.html', 'index.htm', 'index.html'):
            shutil.copy(os.path.join(dirname, html[0]), os.path.join(dirname, 'index.html'))

    def create_record_for_file(self, user, file, type):
        title = us_to_sp(os.path.splitext(os.path.split(file)[1])[0])
        mimetype = MIME_TYPES.get(os.path.splitext(file)[1])
        record = Record.objects.create(owner=user,
                                       name=title,
                                       source='jmutube-%s' % type)
        media = Media.objects.create(record=record,
                             url=file,
                             storage=get_jmutube_storage(),
                             mimetype=mimetype)
        title_field = Field.objects.get(name='title', standard__prefix='dc')
        CollectionItem.objects.create(collection=get_jmutube_collection(), record=record)
        FieldValue.objects.create(record=record,
                                   field=title_field,
                                   value=title,
                                   order=1)
        Tag.objects.add_tag(OwnedWrapper.objects.get_for_object(user=user, object=record), 'JMUtube')
        return record

    def sync_files(self, user):
        # create directories if missing
        for type in FILE_TYPES.keys():
            d = self.path(os.path.join(user.username, type))
            if not os.path.isdir(d):
                os.makedirs(d)
        
        def unify_paths(list):
            return map(lambda s: s.replace('\\', '/').lower(), list)
        logging.debug("Synching files for %s" % user.username)
        media = unify_paths([m.url for m in Media.objects.select_related('record').filter(record__owner=user, storage=get_jmutube_storage())])
#        for m in media:
#            logging.info("Found existing media object %s for %s" % (m, user.username))
        for type, extensions in FILE_TYPES.iteritems():
            subdir = os.path.join(user.username, type)
            files = unify_paths(self.list_files(subdir, extensions))
            for m in media:
                try:
                    files.remove(m)
                except ValueError:
                    pass
            for file in files:
                logging.debug("Creating record for %s owned by %s" % (file, user.username))
                self.create_record_for_file(user, file, type)
