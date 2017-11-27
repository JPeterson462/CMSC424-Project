import os

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import DataAggregate

def index(request):
    data_aggregates_list = DataAggregate.objects.all()
    context = { 'data_aggregates_list': data_aggregates_list }
    return render(request, 'mmda/index.html', context)

def insert_file(request):
    new_dagr = DataAggregate(name=os.path.basename(request.POST['file_path']))
    new_dagr.save()
    return HttpResponseRedirect(reverse('mmda:index'))
