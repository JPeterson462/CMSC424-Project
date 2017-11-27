import datetime
import os

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import DataAggregate, FileMetadata

def index(request):
    data_aggregates_list = DataAggregate.objects.all()
    context = { 'data_aggregates_list': data_aggregates_list }
    return render(request, 'mmda/index.html', context)

def insert_file(request):
    # Grab the file path from the HTTP request
    file_path = request.POST['file_path']

    # Populate the file metadata for the selected file
    metadata = FileMetadata(
        file_name=os.path.basename(file_path),
        storage_path=os.path.dirname(file_path),
        creator_name=os.getlogin(),
        time_created=datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
        last_modified=datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
        document_type_id=0)
    metadata.save()

    # Create the DAGR where the default name is the selected file's name
    new_dagr = DataAggregate(name=os.path.basename(file_path))
    new_dagr.save()
    new_dagr.files.add(metadata)

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))
