from django.shortcuts import render

from .models import DataAggregate

def index(request):
    data_aggregates_list = DataAggregate.objects.all()
    context = { 'data_aggregates_list': data_aggregates_list }
    return render(request, 'mmda/index.html', context)
