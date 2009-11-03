from django.db import models
from django.contrib.auth.models import User

class Computer(models.Model):
    building = models.CharField(max_length=50)
    room = models.CharField(max_length=50)
    mac_address = models.CharField(max_length=12)

    def __unicode__(self):
        return u'%s %s' % (self.building, self.room)

    class Meta:
        ordering = ['building', 'room']

class Schedule(models.Model):
    computer = models.ForeignKey(Computer, verbose_name="room")
    user = models.ForeignKey(User)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __unicode__(self):
        return u'%s from %s to %s for %s' % (self.computer, self.start_time, self.end_time, self.user)
    
    class Meta:
        ordering = ['user', 'start_time']

class Mapping(models.Model):
    time_stamp = models.DateTimeField(auto_now=True)
    source_file = models.CharField(max_length=250)
    target_file = models.CharField(max_length=250)
    user = models.ForeignKey(User, null=True)

    def __unicode__(self):
        return u'%s -> %s at %s for %s' % (self.source_file, self.target_file, self.time_stamp, self.user)
