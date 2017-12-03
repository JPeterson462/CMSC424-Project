import datetime
import glob
import os
import uuid
import requests
import re
import sys

from django.db import connection
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import DataAggregate, FileMetadata
from .parsing import *

DATETIME_FORMAT = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}")

def index(request):
    context = { }
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM dagr
        """)
        context['dagrs_count'] = dictfetchall(cursor)[0]['COUNT(*)']

        cursor.execute("""
            SELECT COUNT(*)
            FROM file_instance
        """)
        context['files_count'] = dictfetchall(cursor)[0]['COUNT(*)']

        cursor.execute("""
            SELECT COUNT(*)
            FROM category
        """)
        context['categories_count'] = dictfetchall(cursor)[0]['COUNT(*)']

        cursor.execute("""
            SELECT COUNT(*)
            FROM file_instance
            WHERE document_type = 0
            UNION ALL
            SELECT COUNT(*)
            FROM file_instance
            WHERE document_type = 1
            UNION ALL
            SELECT COUNT(*)
            FROM file_instance
            WHERE document_type = 2
            UNION ALL
            SELECT COUNT(*)
            FROM file_instance
            WHERE document_type = 3
            UNION ALL
            SELECT COUNT(*)
            FROM file_instance
            WHERE document_type = 4
        """)
        result = dictfetchall(cursor)
        context['other_count'] = result[0]['COUNT(*)']
        context['document_count'] = result[1]['COUNT(*)']
        context['image_count'] = result[2]['COUNT(*)']
        context['audio_count'] = result[3]['COUNT(*)']
        context['video_count'] = result[4]['COUNT(*)']

    return render(request, 'mmda/index.html', context)

def show_categories(request):
    context = { }
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM category c
        """)
        categories = dictfetchall(cursor)
        context['categories'] = categories

    return render(request, 'mmda/categories.html', context)

def data_aggregates(request):
    dagrs_list = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
        """)
        dagrs_list = dictfetchall(cursor)

    context = {
        'dagrs_list': dagrs_list
    }
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
            SELECT ds.*
            FROM dagr_mapping dm
            JOIN dagr ds
                ON dm.child_dagr_guid = ds.dagr_guid
            WHERE dm.parent_dagr_guid = %s
        """, [dagr_guid])
        child_dagrs = dictfetchall(cursor)

        ancestor_dagr_guids = find_ancestors([dagr_guid], sys.maxsize)
        ancestor_dagrs = []
        if ancestor_dagr_guids:
            cursor.execute("""
                SELECT *
                FROM dagr
                WHERE dagr_guid IN %s
            """, [ancestor_dagr_guids])
            ancestor_dagrs = dictfetchall(cursor)

        context = {
            'dagr': dagr,
            'categories': categories,
            'annotations': annotations,
            'document_metadata': document_metadata,
            'image_metadata': image_metadata,
            'audio_metadata': audio_metadata,
            'video_metadata': video_metadata,
            'other_metadata': other_metadata,
            'child_dagrs': child_dagrs,
            'ancestor_dagrs': ancestor_dagrs
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
                    dagr_guid, dagr_name
                ) VALUES (
                    %s, %s
                )
            """, [dagr_guid, os.path.basename(file_path)])
            cursor.execute("""
                INSERT INTO dagr_mapping (
                    parent_dagr_guid, child_dagr_guid
                ) VALUES (
                    %s, %s
                )
            """, [parent_dagr_guid, dagr_guid])
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
                dagr_guid, dagr_name
            ) VALUES (
                %s, %s
            )
        """, [guid, os.path.basename(folder_path) + '/'])
        if parent_dagr_guid:
            cursor.execute("""
                INSERT INTO dagr_mapping (
                    parent_dagr_guid, child_dagr_guid
                ) VALUES (
                    %s, %s
                )
            """, [parent_dagr_guid, guid])

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
    parent_category_id = request.POST['parent_category_target']
    parent_category_null = len(parent_category_id) == 0
    if parent_category_null or parent_category_id == 'undefined':
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
    return HttpResponseRedirect(reverse('mmda:categories'))

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
    return HttpResponseRedirect(reverse('mmda:categories'))

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
    context = {}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE dagr_guid NOT IN (
                SELECT DISTINCT child_dagr_guid
                FROM dagr_mapping
            )
        """)
        context['orphan_dagrs'] = dictfetchall(cursor)

    return render(request, 'mmda/orphan_dagr_report.html', context)

def sterile_dagr_report(request):
    context = {}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE dagr_guid NOT IN (
                SELECT DISTINCT parent_dagr_guid
                FROM dagr_mapping
            )
        """)
        context['sterile_dagrs'] = dictfetchall(cursor)

    return render(request, 'mmda/sterile_dagr_report.html', context)

def time_range_dagr_report(request):
    context = {}

    start_time = datetime.datetime.min
    start_time_str = request.POST.get('start_time', None)
    if start_time_str:
        if DATETIME_FORMAT.search(start_time_str):
            start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        else:
            start_time = datetime.datetime.strptime(start_time_str, '%m/%d/%Y %H:%M %p')
        
    end_time = datetime.datetime.max
    end_time_str = request.POST.get('end_time', None)
    if end_time_str:
        if DATETIME_FORMAT.search(end_time_str):
            end_time = datetime.datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        else:
            end_time = datetime.datetime.strptime(end_time_str, '%m/%d/%Y %H:%M %p')

    # Find all DataAggregates that were created between the start and end times
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE time_created BETWEEN %s AND %s
        """, [start_time, end_time])
        context['dagrs_list'] = dictfetchall(cursor)

    context['start_time'] = start_time.strftime('%m/%d/%Y %H:%M %p')
    context['end_time'] = end_time.strftime('%m/%d/%Y %H:%M %p')
    return render(request, 'mmda/time_range_dagr_report.html', context)

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

def file_metadata(request):
    context = {}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM file_instance fi
            JOIN document_metadata dm
                ON fi.file_guid = dm.file_guid
        """)
        context['document_metadata'] = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_instance fi
            JOIN image_metadata im
                ON fi.file_guid = im.file_guid
        """)
        context['image_metadata'] = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_instance fi
            JOIN audio_metadata am
                ON fi.file_guid = am.file_guid
        """)
        context['audio_metadata'] = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_instance fi
            JOIN video_metadata vm
                ON fi.file_guid = vm.file_guid
        """)
        context['video_metadata'] = dictfetchall(cursor)

        cursor.execute("""
            SELECT *
            FROM file_instance
            WHERE document_type = 0
        """)
        context['other_metadata'] = dictfetchall(cursor)

    return render(request, 'mmda/file_metadata.html', context)

def reachability_report(request, dagr_guid):
    ancestors_or_descendants = request.POST['ancestors_or_descendants']
    num_levels = int(request.POST['num_levels'])

    context = {
        'ancestors_or_descendants': ancestors_or_descendants,
        'num_levels': num_levels
    }

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM dagr
            WHERE dagr_guid = %s
        """, [dagr_guid])
        context['dagr'] = dictfetchall(cursor)[0]

    reachable_dagr_guids = []
    if ancestors_or_descendants == 'ancestors':
        reachable_dagr_guids = find_ancestors([dagr_guid], num_levels)
    else:
        reachable_dagr_guids = find_descendants([dagr_guid], num_levels)

    if reachable_dagr_guids:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM dagr
                WHERE dagr_guid IN %s
            """, [reachable_dagr_guids])
            context['reachable_dagrs'] = dictfetchall(cursor)
    else:
        context['reachable_dagrs'] = []

    return render(request, 'mmda/reachability_report.html', context)

def find_ancestors(dagr_guids, num_levels):
    if num_levels > 0:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT parent_dagr_guid
                FROM dagr_mapping
                WHERE child_dagr_guid IN %s
            """, [dagr_guids])
            parent_dagr_guids = [item['parent_dagr_guid'] for item in dictfetchall(cursor)]
            if parent_dagr_guids:
                return parent_dagr_guids + find_ancestors(parent_dagr_guids, num_levels - 1)
            else:
                return parent_dagr_guids
    else:
        return []

def find_descendants(dagr_guids, num_levels):
    if num_levels > 0:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT child_dagr_guid
                FROM dagr_mapping
                WHERE parent_dagr_guid IN %s
            """, [dagr_guids])
            child_dagr_guids = [item['child_dagr_guid'] for item in dictfetchall(cursor)]
            if child_dagr_guids:
                return child_dagr_guids + find_descendants(child_dagr_guids, num_levels - 1)
            else:
                return child_dagr_guids
    else:
        return []