import tempfile
import unittest
import os
import shutil
import re
from StringIO import StringIO
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from apps.jmutube.util import get_jmutube_collection, get_jmutube_storage, make_unique
from apps.jmutube.jmutubestorage import determine_type


class JmuTubeRepositoryTestCase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.collection = get_jmutube_collection()
        self.storage = get_jmutube_storage()
        self.user = User.objects.create(username='jmutube_test')
        self.storage.storage_system.sync_files(self.user)
        self.delete_files = []

    def tearDown(self):
        for name in self.delete_files:
            self.storage.storage_system.delete(name)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def check_filename(self, filename):
        base, ext = os.path.splitext(filename)
        type = determine_type(filename)
        name = make_unique(os.path.join(self.user.username, type, re.sub(r'[^\w]+', '_', base) + ext.lower()))
        file = ContentFile('hello world')
        self.delete_files.append(name)
        self.storage.save_file(name, file)
        record = self.storage.storage_system.create_record_for_file(self.user, name, type)
        print record.name
        self.assertTrue(len(record.name) > 0)
    
    def test_filenames(self):
        map(self.check_filename, [' .mov', '.mov', '".mov'])
