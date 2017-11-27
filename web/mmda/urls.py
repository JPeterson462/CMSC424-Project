from django.conf.urls import url

from . import views

app_name = 'mmda'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^insert_file/$', views.insert_file, name='insert_file')
]