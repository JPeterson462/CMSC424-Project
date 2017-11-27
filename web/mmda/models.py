import datetime

from django.db import models
from django.utils import timezone

class Metadata(models.Model):
    def __str__(self):
        return "Metadata"

class FileMetadata(models.Model):
    file_name = models.CharField(max_length=200)
    storage_path = models.CharField(max_length=500)
    creator_name = models.CharField(max_length=200)
    time_created = models.DateTimeField()
    last_modified = models.DateTimeField()
    document_type_id = models.PositiveIntegerField()

    def __str__(self):
        return "File Metadata: " + self.file_name

class DocumentMetadata(Metadata):
    file_guid = models.ForeignKey(FileMetadata, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    authors = models.CharField(max_length=500)

    def __str__(self):
        return "Document Metadata: " + self.title


class VideoMetadata(Metadata):
    file_guid = models.ForeignKey(FileMetadata, on_delete=models.CASCADE)
    length = models.CharField(max_length=64)
    file_format = models.CharField(max_length=64)

    def __str__(self):
        return "Video Metadata: " + self.file_format

class AudioMetadata(Metadata):
    file_guid = models.ForeignKey(FileMetadata, on_delete=models.CASCADE)
    length = models.CharField(max_length=64)
    bit_rate = models.CharField(max_length=64)
    mono_or_stereo = models.PositiveIntegerField()
    file_format = models.CharField(max_length=64)

    def __str__(self):
        return "Audio Metadata: " + self.file_format

class ImageMetadata(Metadata):
    file_guid = models.ForeignKey(FileMetadata, on_delete=models.CASCADE)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    file_format = models.CharField(max_length=64)

    def __str__(self):
        return "Image Metadata: " + self.file_format

class DataAggregate(models.Model):
    name = models.CharField(max_length=200)
    time_created = models.DateTimeField(auto_now=True)
    files = models.ManyToManyField(FileMetadata)

    def __str__(self):
        return "Data Aggregate: " + self.name
