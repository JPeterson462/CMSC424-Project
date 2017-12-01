import datetime
import glob
import os
import uuid
import requests

from django.db import connection
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import DataAggregate, FileMetadata
from .parsing import *

def index(request):
    context = { }
    return render(request, 'mmda/index.html', context)

''' def index(request):
    data_aggregates_list = DataAggregate.objects.raw("""
        SELECT *
        FROM mmda_dataaggregate
    """)
    context = { 'data_aggregates_list': data_aggregates_list }
    return render(request, 'mmda/index.html', context) '''

def data_aggregates(request):
    dagrs_list = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
        """)
        dagrs_list = dictfetchall(cursor)

    context = { 'dagrs_list': dagrs_list }
    return render(request, 'mmda/data_aggregates.html', context)

def dagr_page(request, dagr_guid):
    context = {}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE dagr_guid = %s
        """, [dagr_guid])
        dagr = dictfetchall(cursor)[0]

        cursor.execute("""
            SELECT annotation
            FROM annotation
            WHERE dagr_guid = %s
        """, [dagr_guid])
        annotations = dictfetchall(cursor)

        cursor.execute("""
            SELECT cs.category_id, cs.category_name, cm.dagr_guid
            FROM category cs
            LEFT JOIN category_mapping cm
                ON cs.category_id = cm.category_id
        """)
        categories = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_dagr_mapping fdm
            JOIN file_instance fi
                ON fdm.file_guid = fi.file_guid
            JOIN document_metadata dm
                ON fi.file_guid = dm.file_guid
            WHERE fdm.dagr_guid = %s
        """, [dagr_guid])
        document_metadata = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_dagr_mapping fdm
            JOIN file_instance fi
                ON fdm.file_guid = fi.file_guid
            JOIN image_metadata im
                ON fi.file_guid = im.file_guid
            WHERE fdm.dagr_guid = %s
        """, [dagr_guid])
        image_metadata = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_dagr_mapping fdm
            JOIN file_instance fi
                ON fdm.file_guid = fi.file_guid
            JOIN audio_metadata am
                ON fi.file_guid = am.file_guid
            WHERE fdm.dagr_guid = %s
        """, [dagr_guid])
        audio_metadata = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_dagr_mapping fdm
            JOIN file_instance fi
                ON fdm.file_guid = fi.file_guid
            JOIN video_metadata vm
                ON fi.file_guid = vm.file_guid
            WHERE fdm.dagr_guid = %s
        """, [dagr_guid])
        video_metadata = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_dagr_mapping fdm
            JOIN file_instance fi
                ON fdm.file_guid = fi.file_guid
            WHERE fdm.dagr_guid = %s AND fi.document_type = 0
        """, [dagr_guid])
        other_metadata = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE parent_dagr_guid = %s
        """, [dagr_guid])
        child_dagrs = dictfetchall(cursor)

        context = {
            'dagr': dagr,
            'categories': categories,
            'annotations': annotations,
            'document_metadata': document_metadata,
            'image_metadata': image_metadata,
            'audio_metadata': audio_metadata,
            'video_metadata': video_metadata,
            'other_metadata': other_metadata,
            'child_dagrs': child_dagrs
        }

    return render(request, 'mmda/dagr_page.html', context)

def format_date_from_header(header_date):
    return datetime.datetime.strptime(header_date, '%a, %d %b %Y %H:%M:%S %Z')

def create_dagr(file_path, parent_dagr_guid, recursion_level):
    if recursion_level < 2:
        print ("Creating DAGR for: " + file_path)
        dagr_guid = str(uuid.uuid4())
        with connection.cursor() as cursor:
            # Create a new DAGR where the default name is the selected file's name
            cursor.execute("""
                INSERT INTO dagr (
                    dagr_guid, dagr_name, time_created, parent_dagr_guid
                ) VALUES (
                    %s, %s, %s, %s
                )
            """, [dagr_guid, os.path.basename(file_path), datetime.datetime.now(), parent_dagr_guid])
        storage_path = file_path
        if file_path.startswith("http://") or file_path.startswith("https://"):
            r = requests.get(file_path)
            if 'last-modified' in r.headers:
                last_modified = format_date_from_header(r.headers['last-modified'])
            else:
                last_modified = None
            creator_name = None
            time_created = None
        else:
            last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            creator_name = os.getlogin()
            time_created = datetime.datetime.fromtimestamp(os.path.getctime(file_path))

        # Create this file and parse its metadata
        parse_file(file_path, dagr_guid, storage_path, creator_name, time_created, last_modified, create_dagr, recursion_level)

def create_folder_dagr(folder_path, parent_dagr_guid):
    guid = str(uuid.uuid4())
    with connection.cursor() as cursor:
        # Create a new DAGR where the default name is the folder's name
        cursor.execute("""
            INSERT INTO dagr (
                dagr_guid, dagr_name, time_created, parent_dagr_guid
            ) VALUES (
                %s, %s, %s, %s
            )
        """, [guid, os.path.basename(folder_path) + '/', datetime.datetime.now(), parent_dagr_guid])

        # Recursively add DAGRs
        for file in os.listdir(folder_path):
            file_path = folder_path + '/' + file
            if os.path.isdir(file_path):
                create_folder_dagr(file_path, guid)
            else:
                create_dagr(file_path, guid, 0)

def insert_file(request):
    # Grab the file path from the HTTP request
    file_path = request.POST['file_path']
    parent_guid = request.POST['parent_dagr_guid']
    parent_guid_null = len(parent_guid) == 0
    if parent_guid_null:
        parent_guid = None

    create_dagr(file_path, parent_guid, 0)    

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:data_aggregates'))

def bulk_data_insert(request):
    # Grab the folder path from the HTTP request
    folder_path = request.POST['folder_path']
    parent_guid = request.POST['parent_dagr_guid']
    parent_guid_null = len(parent_guid) == 0
    if parent_guid_null:
        parent_guid = None

    create_folder_dagr(folder_path, parent_guid)

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:data_aggregates'))

def html_insert(request):
    # Grab the file path from the HTTP request
    file_path = request.POST['file_path']
    parent_guid = request.POST['parent_guid']
    parent_guid_null = len(parent_guid) == 0
    if parent_guid_null:
        parent_guid = None

    create_dagr(file_path, parent_guid, 0)       

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def create_category(request):
    # Grab the category name from the HTTP request
    category_name = request.POST['category_name']
    parent_category_id = request.POST['parent_category_id']
    parent_category_null = len(parent_category_id) == 0
    if parent_category_null:
        parent_category_id = None
    
    with connection.cursor() as cursor:
        # Insert a new category record into the database
        cursor.execute("""
            INSERT INTO category (
                category_name, parent_category_id
            ) VALUES (
                %s, %s
            )
        """, [category_name, parent_category_id])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def remove_category(request):
    # Get the Category ID from the HTTP request
    category_name = request.POST['category_id']

    with connection.cursor() as cursor:
        # Delete all DAGR to Category mappings that involve this category
        cursor.execute("""
            DELETE FROM category_mapping
            WHERE category_id IN (
                SELECT category_id FROM category
                WHERE category_name = %s
            )
        """, [category_name])

        # Delete the Category record
        cursor.execute("""
            DELETE FROM category
            WHERE category_name = %s
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
            INSERT INTO category_mapping (
                dagr_guid, category_id
            ) VALUES (
                %s, %s
            )
        """, [dagr_id, category_id])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def remove_dagr_from_category(request):
    # Grab the category ID and DAGR ID from the HTTP request
    dagr_id = request.POST['dagr_id']
    category_id = request.POST['category_id']

    with connection.cursor() as cursor:
        # Delete the record that maps the DAGR to the Category
        cursor.execute("""
            DELETE FROM category_mapping
            WHERE dagr_guid = %s AND category_id = %s
        """, [dagr_id, category_id])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def orphan_dagr_report(request):
    # Find all DataAggregates which have no parent DAGRs
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE parent_dagr_guid IS NULL
        """)
        results = dictfetchall(cursor)
        for result in results:
            print(result['dagr_guid'])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def sterile_dagr_report(request):
    # Find all DataAggregates which have no child DAGRs
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE dagr_guid NOT IN (
                SELECT DISTINCT parent_dagr_guid
                FROM dagr
                WHERE parent_dagr_guid IS NOT NULL
            )
        """)
        results = dictfetchall(cursor)
        for result in results:
            print(result['dagr_guid'])

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def time_range_dagr_report(request):
    # Get the start and end times from the HTTP request
    start_time = request.POST['start_time']
    end_time = request.POST['end_time']

    print(start_time)
    print(end_time)

    # Find all DataAggregates that were created between the start and end times
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE time_created BETWEEN %s AND %s
        """, [start_time, end_time])
        results = dictfetchall(cursor)
        for result in results:
            print(result['dagr_guid'])

    context = { 'dagrs_list': dagrs_list }
    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def change_dagr_name(request, dagr_guid):
    new_name = request.POST['new_name']
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE dagr
            SET dagr_name = %s
            WHERE dagr_guid = %s
        """, [new_name, dagr_guid])

    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))

def add_file_to_dagr(request, dagr_guid):
    storage_path = file_path = request.POST['file_path']
    if file_path.startswith("http://") or file_path.startswith("https://"):
        r = requests.get(file_path)
        if 'last-modified' in r.headers:
            last_modified = format_date_from_header(r.headers['last-modified'])
        else:
            last_modified = None
        creator_name = None
        time_created = None
    else:
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        creator_name = os.getlogin()
        time_created = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    
    parse_file(file_path, dagr_guid, storage_path, creator_name, time_created,
               last_modified, create_dagr, recursion_level=0)

    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))

def add_annotation_to_dagr(request, dagr_guid):
    new_annotation = request.POST['new_annotation']
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO annotation (
                dagr_guid, annotation
            ) VALUES (
                %s, %s
            )
        """, [dagr_guid, new_annotation])
    
    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))

def remove_annotation_from_dagr(request, dagr_guid, annotation):
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM annotation
            WHERE dagr_guid = %s AND annotation = %s
        """, [dagr_guid, annotation])

    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))

def add_category_to_dagr(request, dagr_guid):
    category_id = request.POST['category_id']
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO category_mapping (
                dagr_guid, category_id
            ) VALUES (
                %s, %s
            )
        """, [dagr_guid, category_id])

    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))

def remove_category_from_dagr(request, dagr_guid, category_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM category_mapping
            WHERE dagr_guid = %s AND category_id = %s
        """, [dagr_guid, category_id])

    return HttpResponseRedirect(reverse('mmda:dagr_page', kwargs={'dagr_guid': dagr_guid}))