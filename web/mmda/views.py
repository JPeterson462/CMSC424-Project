import datetime
import glob
import os
import uuid

from django.db import connection
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import DataAggregate, FileMetadata
from .parsing import *

def index(request):
    data_aggregates_list = DataAggregate.objects.all()
    context = { 'data_aggregates_list': data_aggregates_list }
    return render(request, 'mmda/index.html', context)

def create_dagr(file_path, parent_dagr_guid):
    guid = str(uuid.uuid4())
    with connection.cursor() as cursor:
        # Create a new DAGR where the default name is the selected file's name
        cursor.execute("""
            INSERT INTO dagr (
                dagr_guid, name, time_created, parent_dagr_guid
            ) VALUES (
                %s, %s, %s, %s
            )
        """, [guid, os.path.basename(file_path), datetime.datetime.now(), parent_dagr_guid])
    storage_path = os.path.dirname(file_path)
    creator_name = os.getlogin()
    time_created = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

    # Create this file and parse its metadata
    parse_file(file_path, guid, storage_path, creator_name, time_created, last_modified)

def create_folder_dagr(folder_path, parent_guid):
    guid = str(uuid.uuid4())
    with connection.cursor() as cursor:
        # Create a new DAGR where the default name is the folder's name
        cursor.execute("""
            INSERT INTO dagr (
                dagr_guid, name, time_created, parent_dagr_guid
            ) VALUES (
                %s, %s, %s, %s
            )
        """, [guid, os.path.basename(file_path), datetime.datetime.now(), parent_dagr_guid])

        # Recursively add DAGRs
        for file in os.listdir(folder_path):
            file_path = folder_path + '/' + file
            if os.path.isdir(file_path):
                create_folder_dagr(file_path, guid)
            else:
                create_dagr(file_path, guid)

def insert_file(request):
    # Grab the file path from the HTTP request
    file_path = request.POST['file_path']
    parent_guid = request.POST['parent_guid']
    parent_guid_null = parent_guid.length() == 0
    if parent_guid_null:
        parent_guid = None

    create_dagr(file_path, parent_guid)    

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def bulk_data_insert(request):
    # Grab the folder path from the HTTP request
    folder_path = request.POST['folder_path']
    parent_guid = request.POST['parent_guid']
    parent_guid_null = parent_guid.length() == 0
    if parent_guid_null:
        parent_guid = None

    create_folder_dagr(folder_path, parent_guid)

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def html_insert(request):
    # Grab the file path from the HTTP request
    file_path = request.POST['file_path']
    parent_guid = request.POST['parent_guid']
    parent_guid_null = parent_guid.length() == 0
    if parent_guid_null:
        parent_guid = None

    create_dagr(file_path, parent_guid)       

    # Redirect the user back to the home page
    return HttpResponseRedirect(reverse('mmda:index'))

def create_category(request):
    # Grab the category name from the HTTP request
    category_name = request.POST['category_name']
    parent_category_id = request.POST['parent_category_id']
    parent_category_null = parent_category_id.length() == 0
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
    category_id = request.POST['category_id']

    with connection.cursor() as cursor:
        # Delete all DAGR to Category mappings that involve this category
        cursor.execute("""
            DELETE FROM category
            WHERE category_id = %s
        """, [category_id])

        # Delete the Category record
        cursor.execute("""
            DELETE FROM category
            WHERE id = %s
        """, [category_id])

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

def orphan_dagr_report(request):
    # Find all DataAggregates which have no parent DAGRs
    orphan_dagrs = DataAggregate.objects.raw("""
        SELECT *
        FROM mmda_dataaggregate
        WHERE parent_dagr_id IS NULL
    """)

    context = { 'orphan_dagrs': orphan_dagrs }
    return render(request, 'mmda/orphan_dagr_report.html', context)

def sterile_dagr_report(request):
    # Find all DataAggregates which have no child DAGRs
    sterile_dagrs = DataAggregate.objects.raw("""
        SELECT *
        FROM mmda_dataaggregate
        WHERE id NOT IN (
            SELECT DISTINCT parent_dagr_id
            FROM mmda_dataaggregate
            WHERE parent_dagr_id IS NOT NULL
        )
    """)

    context = { 'sterile_dagrs': sterile_dagrs }
    return render(request, 'mmda/sterile_dagr_report.html', context)

def time_range_dagr_report(request):
    # Get the start and end times from the HTTP request
    start_time = request.POST['start_time']
    end_time = request.POST['end_time']

    print(start_time)
    print(end_time)

    # Find all DataAggregates that were created between the start and end times
    dagrs_list = DataAggregate.objects.raw("""
        SELECT *
        FROM mmda_dataaggregate
        WHERE time_created BETWEEN %s AND %s
    """, [start_time, end_time])

    context = { 'dagrs_list': dagrs_list }
    return render(request, 'mmda/time_range_dagr_report.html', context)