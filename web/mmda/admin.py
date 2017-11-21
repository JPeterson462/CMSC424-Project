from django.contrib import admin

from .models import DataAggregate, FileMetadata

admin.site.register(DataAggregate)
admin.site.register(FileMetadata)
