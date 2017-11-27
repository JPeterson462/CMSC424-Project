import datetime

from django.db import models
from django.utils import timezone


class FileMetadata(models.Model):
    file_name = models.CharField(max_length=200)
    storage_path = models.CharField(max_length=500)
    creator_name = models.CharField(max_length=200)
    time_created = models.DateTimeField()
    last_modified = models.DateTimeField()
    size = models.PositiveIntegerField(default=0)
    document_type_id = models.PositiveIntegerField()

    def __str__(self):
        return "File Metadata: " + self.file_name


class DataAggregate(models.Model):
    name = models.CharField(max_length=200)
    time_created = models.DateTimeField(auto_now=True)
    files = models.ManyToManyField(FileMetadata)

    def __str__(self):
        return "Data Aggregate: " + self.name
