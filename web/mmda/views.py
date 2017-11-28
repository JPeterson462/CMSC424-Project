import datetime
import glob
import os

from django.db import connection
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

    with connection.cursor() as cursor:
        # Create a new DAGR where the default name is the selected file's name
        cursor.execute("""
            INSERT INTO mmda_dataaggregate (
                name, time_created
            ) VALUES (
	            %s, %s
            )
        """, [os.path.basename(file_path), datetime.datetime.now()])

        # Populate the file metadata for the selected file
        cursor.execute("""
            INSERT INTO mmda_filemetadata (
	            file_name, storage_path, creator_name, time_created, last_modified, document_type_id, size
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )""", [
            os.path.basename(file_path),
            os.path.dirname(file_path),
            os.getlogin(),
            datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
            datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
            0,
            os.path.getsize(file_path)
        ])

        # Map the newly created FileMetadata to the new DAGR
        cursor.execute("""
            INSERT INTO mmda_dataaggregate_files (
	            dataaggregate_id, filemetadata_id
            ) VALUES (
	            (SELECT MAX(id) FROM mmda_dataaggregate),
                (SELECT MAX(id) FROM mmda_filemetadata)
            )""")

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def bulk_data_insert(request):
    # Grab the folder path from the HTTP request
    folder_path = request.POST['folder_path']
    
    with connection.cursor() as cursor:
        # Create a new DAGR where the default name is the folder's name
        cursor.execute("""
            INSERT INTO mmda_dataaggregate (
                name, time_created
            ) VALUES (
	            %s, %s
            )
        """, [os.path.basename(folder_path) + '/', datetime.datetime.now()])

        for file_path in glob.glob(os.path.join(folder_path, '*.*')):
            # Create a new FileMetadata entry
            cursor.execute("""
                INSERT INTO mmda_filemetadata (
                    file_name, storage_path, creator_name, time_created, last_modified, document_type_id, size
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )""", [
                os.path.basename(file_path),
                os.path.dirname(file_path),
                os.getlogin(),
                datetime.datetime.fromtimestamp(os.path.getctime(file_path)),
                datetime.datetime.fromtimestamp(os.path.getmtime(file_path)),
                0,
                os.path.getsize(file_path)
            ])

            # Map the newly created FileMetadata to the new DAGR
            cursor.execute("""
                INSERT INTO mmda_dataaggregate_files (
                    dataaggregate_id, filemetadata_id
                ) VALUES (
                    (SELECT MAX(id) FROM mmda_dataaggregate),
                    (SELECT MAX(id) FROM mmda_filemetadata)
                )""")

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def create_category(request):
    # Grab the category name from the HTTP request
    category_name = request.POST['category_name']
    
    with connection.cursor() as cursor:
        # Insert a new category record into the database
        cursor.execute("""
            INSERT INTO mmda_category (category_name)
            VALUES (%s)
        """, [category_name])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def add_dagr_to_category(request):
    # Grab the category ID and DAGR ID from the HTTP request
    dagr_id = request.POST['dagr_id']
    category_id = request.POST['category_id']
    
    with connection.cursor() as cursor:
        # Insert a new record that maps the DAGR to the Category
        cursor.execute("""
            INSERT INTO mmda_dataaggregate_categories (
                dataaggregate_id, category_id
            ) VALUES (
                %s, %s
            )
        """, [dagr_id, category_id])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))
