from django.urls import path
from . import views

app_name = 'speedtest_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('check-speed/', views.check_speed, name='check_speed'),
    path('export/<str:format>/', views.export_results, name='export_results'),
]