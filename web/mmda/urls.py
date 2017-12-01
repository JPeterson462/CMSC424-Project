from django.conf.urls import url

from . import views

app_name = 'mmda'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^data_aggregates/(?P<dagr_id>[0-9a-z\-]+)/$', views.dagr_page, name='dagr_page'),
    url(r'^data_aggregates/$', views.data_aggregates, name='data_aggregates'),
    url(r'^insert_file/$', views.insert_file, name='insert_file'),
    url(r'^bulk_data_insert/$', views.bulk_data_insert, name='bulk_data_insert'),
    url(r'^html_insert/$', views.html_insert, name='html_insert'),
    url(r'^create_category/$', views.create_category, name='create_category'),
    url(r'^remove_category/$', views.remove_category, name='remove_category'),
    url(r'^add_dagr_to_category/$', views.add_dagr_to_category, name='add_dagr_to_category'),
    url(r'^remove_dagr_from_category/$', views.remove_dagr_from_category, name='remove_dagr_from_category'),
    url(r'^orphan_dagr_report/$', views.orphan_dagr_report, name='orphan_dagr_report'),
    url(r'^sterile_dagr_report/$', views.sterile_dagr_report, name='sterile_dagr_report'),
    url(r'^time_range_dagr_report/$', views.time_range_dagr_report, name='time_range_dagr_report')
]